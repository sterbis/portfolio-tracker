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
    SyncCommand,
    SyncFxRatesCommand,
    SyncInstrumentsCommand,
)
from .events import (
    FxSyncCompleted,
    FxSyncFailed,
    FxSyncProgress,
    FxSyncStarted,
    InstitutionSyncCompleted,
    InstitutionSyncFailed,
    InstitutionSyncStarted,
    InstrumentSyncCompleted,
    InstrumentSyncFailed,
    InstrumentSyncProgress,
    InstrumentSyncStarted,
    SyncEvent,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InstitutionSyncResult:
    connection: InstitutionConnection
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

        with self._user_scoped_read_only_unit_of_work(user_id) as uow:
            connection = uow.institution_connections.get_by_id(command.connection_id)

        yield InstitutionSyncStarted(connection.id, connection.name)

        try:
            with command.path.open("r", encoding="utf-8") as report:
                parser = self._institution_registry.create_report_parser(
                    connection.institution_id, connection.id
                )
                report_transactions = parser.parse(report)

                with self._user_scoped_unit_of_work(user_id) as uow:
                    transaction_dates = self._process_transactions(
                        uow,
                        connection,
                        command.account_ids,
                        report_transactions,
                    )
                    uow.commit()

            yield InstitutionSyncCompleted(
                connection.id,
                connection.name,
            )

        except PortfolioTrackerError as error:
            logger.error("Report import failed: %s", error.message, exc_info=error)
            yield InstitutionSyncFailed(
                connection.id,
                connection.name,
                error,
            )
            return

        if transaction_dates:
            yield from self.sync_fx_rates(SyncFxRatesCommand(dates=transaction_dates))
            yield from self.sync_instruments(SyncInstrumentsCommand(new_only=True))

    async def sync(
        self, user_id: str, command: SyncCommand
    ) -> AsyncGenerator[SyncEvent, None]:
        connections = self._resolve_institution_connections(user_id, command)
        for connection in connections:
            logger.info(
                "Syncing institution account '%s' (%s)",
                connection.name,
                connection.id,
            )
            yield InstitutionSyncStarted(connection.id, connection.name)

        tasks = [
            asyncio.create_task(
                self._sync_institution_task(connection, command),
            )
            for connection in connections
        ]

        transaction_dates: set[date] = set()

        for future in asyncio.as_completed(tasks):
            result = await future
            if result.is_success:
                transaction_dates.update(result.transaction_dates)

                logger.info(
                    "'%s' (%s) sync completed.",
                    result.connection.name,
                    result.connection.id,
                )
                yield InstitutionSyncCompleted(
                    result.connection.id,
                    result.connection.name,
                )

            else:
                assert result.error is not None
                logger.error(
                    "'%s' (%s) sync failed: %s",
                    result.connection.name,
                    result.connection.id,
                    result.error,
                    exc_info=result.error,
                )
                yield InstitutionSyncFailed(
                    result.connection.id,
                    result.connection.name,
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

    async def _sync_institution_task(
        self,
        connection: InstitutionConnection,
        command: SyncCommand,
    ) -> InstitutionSyncResult:
        try:
            return await self._sync_institution(connection, command)

        except PortfolioTrackerError as error:
            return InstitutionSyncResult(connection, error=error)

    async def _sync_institution(
        self,
        connection: InstitutionConnection,
        command: SyncCommand,
    ) -> InstitutionSyncResult:
        credentials = self._get_credentials(connection.id)
        client = self._institution_registry.create_client(credentials)

        start, end = self._resolve_sync_interval(connection, command)
        report = client.fetch_report(start, end)

        parser = self._institution_registry.create_report_parser(
            connection.institution_id, connection.id
        )
        transaction_dates: set[date] = set()

        with self._user_scoped_unit_of_work(connection.user_id) as uow:
            async for report_chunk in report:
                account_ids = uow.account_map.institution_connection_id_to_account_ids[
                    connection.id
                ]
                required_account_ids = command.account_ids.intersection(account_ids)
                report_transactions = parser.parse(report_chunk)
                new_transaction_dates = self._process_transactions(
                    uow,
                    connection,
                    required_account_ids,
                    report_transactions,
                )
                transaction_dates.update(new_transaction_dates)

            if connection.last_synced_at is None or end > connection.last_synced_at:
                connection = connection.with_last_synced_at(end)
                uow.institution_connections.update(connection)

            uow.commit()

        return InstitutionSyncResult(connection, transaction_dates)

    def _process_transactions(
        self,
        uow: UserScopedUnitOfWork,
        connection: InstitutionConnection,
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
                    institution_connection_id=connection.id,
                    external_id=account_external_id,
                    name=f"{connection.name} account [{account_external_id}]",
                    is_active=True,
                )
                uow.accounts.ensure(account)
                account_id = account.id
                uow.account_map.add_account(account)

            if required_account_ids and account_id not in required_account_ids:
                continue

            if account_id in ignored_account_ids:
                continue

            if report_transaction.instrument:
                main_instrument, underlying_instruments = self._resolve_instrument(
                    report_transaction.instrument, connection.institution_id
                )
                instrument_id = main_instrument.id

                for instrument in reversed([main_instrument] + underlying_instruments):
                    if instrument.id not in instrument_ids:
                        uow.instruments.ensure(instrument)
                        instrument_ids.add(instrument.id)

            else:
                instrument_id = None

            transaction = self._resolve_transaction(
                report_transaction, account_id, instrument_id
            )
            uow.transactions.ensure(transaction)
            transaction_dates.add(transaction.executed_at.date())

        return transaction_dates

    def sync_fx_rates(
        self, command: SyncFxRatesCommand
    ) -> Generator[SyncEvent, None, None]:
        with self._read_only_unit_of_work() as uow:
            if command.all:
                transaction_dates = uow.transactions.get_distinct_dates()
            else:
                transaction_dates = command.dates

            missing_dates = uow.fx_rates.get_missing_dates(
                transaction_dates,
                self._fx_service.base_currency,
                self._fx_service.quote_currencies,
            )

        if not missing_dates:
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

            with self._storage_connection_factory.create() as storage:
                write_uow = storage.unit_of_work()
                for rates in rates_series:
                    with write_uow:
                        write_uow.fx_rates.ensure(rates)
                        write_uow.commit()

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

        with self._read_only_unit_of_work() as uow:
            metadata_list = uow.instruments.get_metadata(filter_=filter_)

        total = len(metadata_list)
        if total == 0:
            return

        yield InstrumentSyncStarted(total)

        completed = 0
        failed_metadata_list: list[InstrumentMetadata] = []

        with self._storage_connection_factory.create() as storage:
            write_uow = storage.unit_of_work()
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
                    with write_uow:
                        write_uow.market_data.ensure_stock_splits(splits)
                        write_uow.instruments.update_last_synced_at(
                            instrument_id=splits.instrument_id,
                            last_synced_at=now,
                        )
                        write_uow.commit()

                completed += 1
                yield InstrumentSyncProgress(completed, total)

        if failed_metadata_list:
            symbols = ", ".join(metadata.symbol for metadata in failed_metadata_list)
            yield InstrumentSyncFailed(
                error=MarketDataIntegrityError(
                    f"Failed to fetch stock splits for following instruments: {symbols}."
                )
            )
        else:
            yield InstrumentSyncCompleted()

    def _get_credentials(self, connection_id: str) -> Credentials:
        with self._read_only_unit_of_work() as uow:
            credentials = uow.credentials.get(connection_id)
            if not credentials:
                raise CredentialsNotFoundError(connection_id)

            return credentials

    def _resolve_institution_connections(
        self, user_id: str, command: SyncCommand
    ) -> list[InstitutionConnection]:
        with self._user_scoped_read_only_unit_of_work(user_id) as uow:
            connection_ids = uow.account_map.resolve_institution_connection_ids(
                command.connection_ids,
                command.account_ids,
            )
            return uow.institution_connections.get_by_ids(connection_ids)

    def _resolve_sync_interval(
        self,
        connection: InstitutionConnection,
        command: SyncCommand,
    ) -> tuple[datetime, datetime]:
        now = datetime.now(tz=timezone.utc)
        account_opened_at = datetime.combine(
            connection.sync_from,
            time.min,
            tzinfo=timezone.utc,
        )
        if command.restore:
            start = account_opened_at - timedelta(days=1)
            end = connection.last_synced_at or now

        else:
            start = command.start or (
                (connection.last_synced_at or account_opened_at) - timedelta(days=1)
            )
            end = command.end or now

        return start, end

    def _resolve_transaction(
        self,
        report_transaction: ReportTransaction,
        account_id: str,
        instrument_id: str | None = None,
    ) -> Transaction:
        return Transaction(
            correlation_id=report_transaction.correlation_id,
            executed_at=report_transaction.executed_at,
            account_id=account_id,
            type=report_transaction.type,
            instrument_id=instrument_id,
            quantity=report_transaction.quantity,
            price=report_transaction.price,
            fee=report_transaction.fee,
            tax=report_transaction.tax,
            cash_impact=report_transaction.cash_impact,
        )

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
