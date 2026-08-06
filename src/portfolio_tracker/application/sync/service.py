import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import AsyncGenerator, Callable, Generator, Iterator

from filterutils import FilterNode, Operator

from portfolio_tracker.application.persistence import UserScopedUnitOfWork
from portfolio_tracker.application.shared.exceptions import (
    CredentialsNotFoundError,
    FxClientError,
    FxDataIntegrityError,
    InstitutionReportNotFoundError,
    MarketDataClientError,
    MarketDataIntegrityError,
)
from portfolio_tracker.application.shared.service import ApplicationService
from portfolio_tracker.application.shared.exceptions import ApplicationError
from portfolio_tracker.application.fx import FxService
from portfolio_tracker.application.institution import (
    InstitutionClient,
    InstitutionReportParser,
    ReportInstrument,
    ReportTransaction,
)
from portfolio_tracker.application.market_data import (
    MarketDataService,
)
from portfolio_tracker.application.persistence import SessionFactory
from portfolio_tracker.domain.account import (
    AssetAccount,
    InstitutionAccount,
)
from portfolio_tracker.domain.institution import Credentials, InstitutionId
from portfolio_tracker.domain.instrument import (
    DerivativeInstrumentBaseData,
    Instrument,
    InstrumentMetadata,
    InstrumentBaseData,
    create_instrument,
)
from portfolio_tracker.domain.transaction import Transaction
from portfolio_tracker.shared.async_utils import as_async_generator

from .commands import (
    ImportReportCommand,
    SyncInstitutionAccountsCommand,
    SyncFxRatesCommand,
    SyncInstrumentsCommand,
)
from .events import (
    InstitutionAccountSyncCompleted,
    InstitutionAccountSyncFailed,
    InstitutionAccountSyncStarted,
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
class InstitutionAccountSyncResult:
    institution_account: InstitutionAccount
    transaction_dates: set[date] = field(default_factory=set)
    error: Exception | None = None

    @property
    def is_success(self) -> bool:
        return self.error is None


class SyncService(ApplicationService):
    def __init__(
        self,
        session_factory: SessionFactory,
        fx_service: FxService,
        market_data_service: MarketDataService,
        client_factory: Callable[
            [InstitutionId, Credentials], InstitutionClient[Credentials]
        ],
        parser_factory: Callable[[InstitutionId, str], InstitutionReportParser],
    ) -> None:
        super().__init__(session_factory)
        self._fx_service = fx_service
        self._market_data_service = market_data_service
        self._client_factory = client_factory
        self._parser_factory = parser_factory

    def import_report(
        self, user_id: str, command: ImportReportCommand
    ) -> Generator[SyncEvent, None, None]:
        if not command.report_path.is_file():
            raise InstitutionReportNotFoundError()

        with self._user_unit_of_work(user_id, read_only=True) as uow:
            institution_account = uow.accounts.get_institution_account_by_id(
                command.institution_account_id
            )

        yield InstitutionAccountSyncStarted(
            account_id=institution_account.id, account_name=institution_account.name
        )

        try:
            parser = self._parser_factory(
                institution_account.institution_id, institution_account.id
            )
            report = command.report_path.open("r", encoding="utf-8")
            report_transactions = parser.parse_report(report)

            with self._user_unit_of_work(user_id) as uow:
                transaction_dates = self._process_transactions(
                    uow,
                    institution_account,
                    command.asset_account_ids,
                    report_transactions,
                )
                uow.commit()

            yield InstitutionAccountSyncCompleted(
                account_id=institution_account.id,
                account_name=institution_account.name,
            )

        except ApplicationError as error:
            logger.error("Report import failed: %s", error.message, exc_info=error)
            yield InstitutionAccountSyncFailed(
                institution_account.id,
                institution_account.name,
                error,
            )
            return

        if transaction_dates:
            yield from self.sync_fx_rates(SyncFxRatesCommand(dates=transaction_dates))

        yield from self.sync_instruments(SyncInstrumentsCommand(new_only=True))

    async def sync_institution_accounts(
        self, user_id: str, command: SyncInstitutionAccountsCommand
    ) -> AsyncGenerator[SyncEvent, None]:
        institution_accounts = self._resolve_synced_accounts(user_id, command)
        for institution_account in institution_accounts:
            yield InstitutionAccountSyncStarted(
                account_id=institution_account.id, account_name=institution_account.name
            )

        tasks = [
            asyncio.create_task(
                self._sync_institution_account_task(institution_account, command),
            )
            for institution_account in institution_accounts
        ]

        transaction_dates: set[date] = set()

        for future in asyncio.as_completed(tasks):
            result = await future
            if result.is_success:
                transaction_dates.update(result.transaction_dates)
                yield InstitutionAccountSyncCompleted(
                    account_id=result.institution_account.id,
                    account_name=result.institution_account.name,
                )
            else:
                assert result.error is not None
                logger.error(
                    "'%s' account sync failed: %s",
                    result.institution_account.name,
                    result.error,
                    exc_info=result.error,
                )
                yield InstitutionAccountSyncFailed(
                    account_id=result.institution_account.id,
                    account_name=result.institution_account.name,
                    error=result.error,
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

    async def _sync_institution_account_task(
        self,
        institution_account: InstitutionAccount,
        command: SyncInstitutionAccountsCommand,
    ) -> InstitutionAccountSyncResult:
        try:
            return await self._sync_institution_account(institution_account, command)
        except ApplicationError as error:
            return InstitutionAccountSyncResult(
                institution_account,
                error=error,
            )

    async def _sync_institution_account(
        self,
        institution_account: InstitutionAccount,
        command: SyncInstitutionAccountsCommand,
    ) -> InstitutionAccountSyncResult:
        credentials = self._get_credentials(institution_account.id)
        client = self._client_factory(institution_account.institution_id, credentials)

        start, end = self._resolve_sync_interval(institution_account, command)
        report = client.fetch_report(start, end)

        parser = self._parser_factory(
            institution_account.institution_id, institution_account.id
        )
        transaction_dates: set[date] = set()

        with self._user_unit_of_work(institution_account.user_id) as uow:
            async for report_chunk in report:
                asset_account_ids = command.asset_account_ids.intersection(
                    uow.accounts_map.institution_to_asset_account_ids[
                        institution_account.id
                    ]
                )
                report_transactions = parser.parse_report(report_chunk)
                report_transaction_dates = self._process_transactions(
                    uow,
                    institution_account,
                    asset_account_ids,
                    report_transactions,
                )
                transaction_dates.update(report_transaction_dates)

            if (
                institution_account.last_synced_at is None
                or end > institution_account.last_synced_at
            ):
                institution_account = institution_account.with_last_synced_at(end)
                uow.accounts.update_institution_account(institution_account)

            uow.commit()

        return InstitutionAccountSyncResult(institution_account, transaction_dates)

    def _process_transactions(
        self,
        uow: UserScopedUnitOfWork,
        institution_account: InstitutionAccount,
        required_asset_account_ids: set[str],
        report_transactions: Iterator[ReportTransaction],
    ) -> set[date]:
        transaction_dates: set[date] = set()
        instrument_ids: set[str] = set()
        ignored_asset_account_ids = (
            uow.accounts_map.deactivated_asset_account_ids - required_asset_account_ids
        )

        for report_transaction in report_transactions:
            external_id = report_transaction.external_asset_account_id

            asset_account_id = uow.accounts_map.external_to_asset_account_id.get(
                external_id
            )
            if not asset_account_id:
                if required_asset_account_ids:
                    continue

                asset_account = AssetAccount(
                    institution_account_id=institution_account.id,
                    external_id=external_id,
                    name=f"{institution_account.name} asset account [{external_id}]",
                    is_active=True,
                )
                uow.accounts.ensure_asset_account(asset_account)
                asset_account_id = asset_account.id
                uow.accounts_map.add_asset_account(asset_account)

            if (
                required_asset_account_ids
                and asset_account_id not in required_asset_account_ids
            ):
                continue

            if asset_account_id in ignored_asset_account_ids:
                continue

            transaction, instruments = self._resolve_transaction(
                report_transaction,
                asset_account_id,
                institution_account.institution_id,
            )
            for instrument in reversed(instruments):
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

            rates_dates = uow.fx_rates.get_distinct_dates()

        missing_dates = transaction_dates - rates_dates
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

            with self._session_factory.create() as session:
                uow = session.unit_of_work()
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

        if not_fetched_dates := (missing_dates - fetched_dates):
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
        if command.all:
            filter_ = None
        elif command.new_only:
            filter_ = FilterNode("last_synced_at", Operator.EQ, None)
        elif command.symbols:
            filter_ = FilterNode("symbol", Operator.IN, command.symbols)
        else:
            filter_ = FilterNode("last_synced_at", Operator.LT, now - timedelta(days=1))

        with self._unit_of_work(read_only=True) as uow:
            metadata_list = uow.instruments.get_metadata(filter_=filter_)

        total = len(metadata_list)
        if total == 0:
            yield InstrumentsSyncCompleted()
            return

        yield InstrumentsSyncStarted(total)

        completed = 0
        failed_metadata_list: list[InstrumentMetadata] = []

        with self._session_factory.create() as session:
            uow = session.unit_of_work()
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

    def _get_credentials(self, account_id: str) -> Credentials:
        with self._unit_of_work(read_only=True) as uow:
            credentials = uow.credentials.retrieve(account_id)
            if not credentials:
                raise CredentialsNotFoundError(account_id)

            return credentials

    def _resolve_synced_accounts(
        self, user_id: str, command: SyncInstitutionAccountsCommand
    ) -> list[InstitutionAccount]:
        with self._user_unit_of_work(user_id, read_only=True) as uow:
            institution_account_ids = uow.accounts_map.resolve_institution_account_ids(
                command.institution_account_ids,
                command.asset_account_ids,
            )
            institution_accounts = uow.accounts.get_institution_accounts_by_ids(
                institution_account_ids
            )
            return institution_accounts

    def _resolve_sync_interval(
        self,
        institution_account: InstitutionAccount,
        command: SyncInstitutionAccountsCommand,
    ) -> tuple[datetime, datetime]:
        now = datetime.now(tz=timezone.utc)
        created_at = datetime.combine(
            institution_account.created_on,
            time.min,
            tzinfo=timezone.utc,
        )
        if command.restore:
            start = created_at - timedelta(days=1)
            end = institution_account.last_synced_at or now

        else:
            start = command.start or (
                (institution_account.last_synced_at or created_at) - timedelta(days=1)
            )
            end = command.end or now

        return start, end

    def _resolve_transaction(
        self,
        report_transaction: ReportTransaction,
        asset_account_id: str,
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
            instruments = [main_instrument] + underlying_instruments

        transaction = Transaction(
            correlation_id=report_transaction.correlation_id,
            executed_at=report_transaction.executed_at,
            asset_account_id=asset_account_id,
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
