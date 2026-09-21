import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import AsyncGenerator, Generator, Iterator

from filterutils import Filter, FilterNode, FilterTree, LogicalOperator, Operator

from portfolio_tracker.application.fx import FxService
from portfolio_tracker.application.institution import (
    InstitutionRegistry,
    ReportInstrument,
    ReportTransaction,
)
from portfolio_tracker.application.market_data import (
    MarketDataService,
)
from portfolio_tracker.application.persistence import (
    StorageConnectionFactory,
    UserScopedUnitOfWork,
)
from portfolio_tracker.application.shared.errors import (
    CredentialsNotFoundError,
    FxClientError,
    FxDataIntegrityError,
    InstitutionReportNotFoundError,
    MarketDataClientError,
    MarketDataIntegrityError,
    PortfolioTrackerError,
)
from portfolio_tracker.application.shared.service import Service
from portfolio_tracker.domain.account import AssetAccount
from portfolio_tracker.domain.institution import Credentials, InstitutionConnection
from portfolio_tracker.domain.instrument import (
    DerivativeInstrumentBaseData,
    Instrument,
    InstrumentBaseData,
    InstrumentMetadata,
    create_instrument,
)
from portfolio_tracker.domain.transaction import Transaction
from portfolio_tracker.shared.async_utils import as_async_generator

from .commands import (
    ImportReportCommand,
    SyncAccountsCommand,
    SyncFxRatesCommand,
    SyncInstrumentsCommand,
)
from .events import (
    AccountsSyncCompleted,
    AccountsSyncFailed,
    AccountsSyncStarted,
    FxSyncCompleted,
    FxSyncFailed,
    FxSyncProgress,
    FxSyncStarted,
    InstrumentsSyncCompleted,
    InstrumentsSyncFailed,
    InstrumentsSyncProgress,
    InstrumentsSyncStarted,
    SyncEvent,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AccountsSyncResult:
    institution_connection: InstitutionConnection
    transaction_dates: set[date] = field(default_factory=set)
    error: Exception | None = None

    @property
    def is_success(self) -> bool:
        return self.error is None


class SyncService(Service):
    def __init__(
        self,
        storage_connection_factory: StorageConnectionFactory,
        institution_registry: InstitutionRegistry,
        fx_service: FxService,
        market_data_service: MarketDataService,
    ) -> None:
        super().__init__(storage_connection_factory)
        self._institution_registry = institution_registry
        self._fx_service = fx_service
        self._market_data_service = market_data_service

    def import_report(
        self, user_id: str, command: ImportReportCommand
    ) -> Generator[SyncEvent, None, None]:
        if not command.path.is_file():
            raise InstitutionReportNotFoundError()

        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            institution_connection = uow.institution_connections.get_by_id(
                command.institution_connection_id
            )

        yield AccountsSyncStarted(
            institution_connection.id, institution_connection.name
        )

        try:
            with command.path.open("r", encoding="utf-8") as report:
                parser = self._institution_registry.create_report_parser(
                    institution_connection.institution_id, institution_connection.id
                )
                report_transactions = parser.parse(report)

                with self._user_scoped_unit_of_work(user_id) as uow:
                    transaction_dates = self._process_transactions(
                        uow,
                        institution_connection,
                        command.account_ids,
                        report_transactions,
                    )
                    uow.commit()

            yield AccountsSyncCompleted(
                institution_connection.id,
                institution_connection.name,
            )

        except PortfolioTrackerError as error:
            logger.error("Report import failed: %s", error.message, exc_info=error)
            yield AccountsSyncFailed(
                institution_connection.id,
                institution_connection.name,
                error,
            )
            return

        if transaction_dates:
            yield from self.sync_fx_rates(SyncFxRatesCommand(dates=transaction_dates))

        yield from self.sync_instruments(SyncInstrumentsCommand(new_only=True))

    async def sync_accounts(
        self, user_id: str, command: SyncAccountsCommand
    ) -> AsyncGenerator[SyncEvent, None]:
        institution_connections = self._resolve_institution_connections(
            user_id, command
        )
        for institution_connection in institution_connections:
            yield AccountsSyncStarted(
                institution_connection.id, institution_connection.name
            )

        tasks = [
            asyncio.create_task(
                self._sync_institution_accounts_task(institution_connection, command),
            )
            for institution_connection in institution_connections
        ]

        transaction_dates: set[date] = set()

        for future in asyncio.as_completed(tasks):
            result = await future
            if result.is_success:
                transaction_dates.update(result.transaction_dates)
                yield AccountsSyncCompleted(
                    result.institution_connection.id,
                    result.institution_connection.name,
                )
            else:
                assert result.error is not None
                logger.error(
                    "'%s' accounts sync failed: %s",
                    result.institution_connection.name,
                    result.error,
                    exc_info=result.error,
                )
                yield AccountsSyncFailed(
                    result.institution_connection.id,
                    result.institution_connection.name,
                    result.error,
                )

        if transaction_dates:
            async for event in as_async_generator(
                self.sync_fx_rates(SyncFxRatesCommand(dates=transaction_dates))
            ):
                yield event

        async for event in as_async_generator(
            self.sync_instruments(SyncInstrumentsCommand(new_only=True))
        ):
            yield event

    async def _sync_institution_accounts_task(
        self,
        institution_connection: InstitutionConnection,
        command: SyncAccountsCommand,
    ) -> AccountsSyncResult:
        try:
            return await self._sync_institution_accounts(
                institution_connection, command
            )
        except PortfolioTrackerError as error:
            return AccountsSyncResult(
                institution_connection,
                error=error,
            )

    async def _sync_institution_accounts(
        self,
        institution_connection: InstitutionConnection,
        command: SyncAccountsCommand,
    ) -> AccountsSyncResult:
        credentials = self._get_credentials(institution_connection.id)
        client = self._institution_registry.create_client(credentials)

        start, end = self._resolve_sync_interval(institution_connection, command)
        report = client.fetch_report(start, end)

        parser = self._institution_registry.create_report_parser(
            institution_connection.institution_id, institution_connection.id
        )
        transaction_dates: set[date] = set()

        with self._user_scoped_unit_of_work(institution_connection.user_id) as uow:
            async for report_chunk in report:
                account_ids = uow.account_map.institution_connection_id_to_account_ids[
                    institution_connection.id
                ]
                required_account_ids = command.account_ids.intersection(account_ids)
                report_transactions = parser.parse(report_chunk)
                report_transaction_dates = self._process_transactions(
                    uow,
                    institution_connection,
                    required_account_ids,
                    report_transactions,
                )
                transaction_dates.update(report_transaction_dates)

            if (
                institution_connection.last_synced_at is None
                or end > institution_connection.last_synced_at
            ):
                institution_connection = institution_connection.with_last_synced_at(end)
                uow.institution_connections.update(institution_connection)

            uow.commit()

        return AccountsSyncResult(institution_connection, transaction_dates)

    def _process_transactions(
        self,
        uow: UserScopedUnitOfWork,
        institution_connection: InstitutionConnection,
        required_account_ids: set[str],
        report_transactions: Iterator[ReportTransaction],
    ) -> set[date]:
        transaction_dates: set[date] = set()
        instrument_ids: set[str] = set()
        ignored_account_ids = (
            uow.account_map.deactivated_account_ids - required_account_ids
        )

        for report_transaction in report_transactions:
            account_external_id = report_transaction.account_external_id
            account_id = uow.account_map.account_external_id_to_account_id.get(
                account_external_id
            )

            if not account_id:
                if required_account_ids:
                    continue

                account = AssetAccount(
                    institution_connection_id=institution_connection.id,
                    external_id=account_external_id,
                    name=f"{institution_connection.name} account [{account_external_id}]",
                    is_active=True,
                )
                uow.accounts.ensure(account)
                account_id = account.id
                uow.account_map.add_account(account)

            if required_account_ids and account_id not in required_account_ids:
                continue

            if account_id in ignored_account_ids:
                continue

            transaction, instruments = self._resolve_transaction(
                report_transaction,
                account_id,
                institution_connection.institution_id,
            )
            for instrument in instruments:
                if instrument.id not in instrument_ids:
                    uow.instruments.ensure(instrument)
                    instrument_ids.add(instrument.id)

            uow.transactions.ensure(transaction)
            transaction_dates.add(report_transaction.executed_at.date())

        return transaction_dates

    def sync_fx_rates(
        self, command: SyncFxRatesCommand
    ) -> Generator[SyncEvent, None, None]:
        with self._unit_of_work(read_only=True) as uow:
            if command.all:
                transaction_dates = uow.transactions.get_distinct_dates()
            else:
                transaction_dates = command.dates

            rate_dates = uow.fx_rates.get_distinct_dates()

        missing_dates = transaction_dates - rate_dates
        if not missing_dates:
            yield FxSyncCompleted()
            return

        total = len(missing_dates)
        completed = 0
        fetched_dates: set[date] = set()

        yield FxSyncStarted(total)

        try:
            rates_series = self._fx_service.get_rates_series(
                from_date=min(missing_dates),
                to_date=max(missing_dates),
                only_dates=missing_dates,
            )

            with self._storage_connection_factory.create() as connection:
                uow = connection.unit_of_work()
                for rates in rates_series:
                    with uow:
                        uow.fx_rates.ensure(rates)
                        uow.commit()

                    completed += 1
                    fetched_dates.add(rates.effective_on)
                    yield FxSyncProgress(completed, total)

        except FxClientError as error:
            logger.error("Failed to fetch FX reates: %s", error.message, exc_info=error)
            yield FxSyncFailed(error)
            return

        if not_fetched_dates := missing_dates - fetched_dates:
            formatted_dates = ", ".join(
                not_fetched_date.isoformat()
                for not_fetched_date in sorted(not_fetched_dates)
            )
            yield FxSyncFailed(
                error=FxDataIntegrityError(
                    f"Failed to fetch FX rates for following dates: {formatted_dates}."
                )
            )
            return

        yield FxSyncCompleted()

    def sync_instruments(
        self, command: SyncInstrumentsCommand
    ) -> Generator[SyncEvent, None, None]:
        now = datetime.now(tz=timezone.utc)
        not_synced_filter = FilterNode("last_synced_at", Operator.EQ, None, Instrument)

        if command.all:
            filter_: Filter | None = None
        elif command.new_only:
            filter_ = not_synced_filter
        elif command.symbols:
            filter_ = FilterNode("symbol", Operator.IN, command.symbols, Instrument)
        else:
            filter_ = FilterTree(LogicalOperator.OR)
            filter_.add_child(not_synced_filter)
            filter_.add_child(
                FilterNode(
                    "last_synced_at", Operator.LT, now - timedelta(days=1), Instrument
                )
            )
        with self._unit_of_work(read_only=True) as uow:
            metadata_list = uow.instruments.get_metadata(filter_=filter_)

        total = len(metadata_list)
        if total == 0:
            yield InstrumentsSyncCompleted()
            return

        yield InstrumentsSyncStarted(total)

        completed = 0
        failed_metadata_list: list[InstrumentMetadata] = []

        with self._storage_connection_factory.create() as connection:
            uow = connection.unit_of_work()
            for metadata in metadata_list:
                try:
                    splits = self._market_data_service.get_stock_splits(metadata)
                except MarketDataClientError as error:
                    logger.error(
                        "Failed to fetch instrument %s stock splits.",
                        metadata.symbol,
                        exc_info=error,
                    )
                    failed_metadata_list.append(metadata)
                    continue

                if splits:
                    with uow:
                        uow.market_data.ensure_stock_splits(splits)
                        uow.instruments.update_last_synced_at(
                            instrument_id=splits.instrument_id,
                            last_synced_at=now,
                        )
                        uow.commit()

                completed += 1
                yield InstrumentsSyncProgress(completed, total)

        if failed_metadata_list:
            symbols = ", ".join(metadata.symbol for metadata in failed_metadata_list)
            yield InstrumentsSyncFailed(
                error=MarketDataIntegrityError(
                    f"Failed to fetch stock splits for following instruments: {symbols}."
                )
            )
        else:
            yield InstrumentsSyncCompleted()

    def _get_credentials(self, institution_connection_id: str) -> Credentials:
        with self._unit_of_work(read_only=True) as uow:
            credentials = uow.credentials.get(institution_connection_id)
            if not credentials:
                raise CredentialsNotFoundError(institution_connection_id)

            return credentials

    def _resolve_institution_connections(
        self, user_id: str, command: SyncAccountsCommand
    ) -> list[InstitutionConnection]:
        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            institution_connection_ids = (
                uow.account_map.resolve_institution_connection_ids(
                    command.institution_connection_ids,
                    command.account_ids,
                )
            )
            return uow.institution_connections.get_by_ids(institution_connection_ids)

    def _resolve_sync_interval(
        self,
        institution_connection: InstitutionConnection,
        command: SyncAccountsCommand,
    ) -> tuple[datetime, datetime]:
        now = datetime.now(tz=timezone.utc)
        account_opened_at = datetime.combine(
            institution_connection.account_opened_on,
            time.min,
            tzinfo=timezone.utc,
        )
        if command.restore:
            start = account_opened_at - timedelta(days=1)
            end = institution_connection.last_synced_at or now

        else:
            start = command.start or (
                (institution_connection.last_synced_at or account_opened_at)
                - timedelta(days=1)
            )
            end = command.end or now

        return start, end

    def _resolve_transaction(
        self,
        report_transaction: ReportTransaction,
        account_id: str,
        institution_id: str,
    ) -> tuple[Transaction, list[Instrument]]:
        main_instrument_id = None
        instruments: list[Instrument] = []

        if report_transaction.instrument:
            main_instrument, underlying_instruments = self._resolve_instrument(
                report_transaction.instrument,
                institution_id,
            )
            main_instrument_id = main_instrument.id
            instruments = list(reversed(underlying_instruments)) + [main_instrument]

        transaction = Transaction(
            correlation_id=report_transaction.correlation_id,
            executed_at=report_transaction.executed_at,
            account_id=account_id,
            type=report_transaction.type,
            instrument_id=main_instrument_id,
            quantity=report_transaction.quantity,
            price=report_transaction.price,
            fee=report_transaction.fee,
            tax=report_transaction.tax,
            cash_impact=report_transaction.cash_impact,
        )

        return transaction, instruments

    def _resolve_instrument(
        self, report_instrument: ReportInstrument, institution_id: str
    ) -> tuple[Instrument, list[Instrument]]:
        base_data: InstrumentBaseData = {
            "name": report_instrument.name,
            "symbol": report_instrument.symbol,
            "exchange": report_instrument.exchange,
            "currency": report_instrument.currency,
        }
        underlying_instruments: list[Instrument] = []
        derivative_base_data: DerivativeInstrumentBaseData | None = None

        if report_instrument.type.is_derivative:
            if report_instrument.underlying_instrument is None:
                raise ValueError(
                    "No underlying instrument provided for "
                    f"derivative instrument type {report_instrument.type}."
                )

            underlying_instrument, other_instruments = self._resolve_instrument(
                report_instrument.underlying_instrument, institution_id
            )
            underlying_instruments = [underlying_instrument] + other_instruments
            derivative_base_data = {
                "underlying_instrument_id": underlying_instrument.id,
                "asset_class": underlying_instrument.asset_class,
            }

        main_instrument = create_instrument(
            report_instrument.type,
            base_data,
            report_instrument.details,
            derivative_base_data,
        )

        return main_instrument, underlying_instruments
