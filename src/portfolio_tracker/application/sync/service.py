import asyncio
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterator

from filterutils import FilterNode, Operator

from portfolio_tracker.application.account import (
    CredentialsNotFoundError,
    InstitutionAccountNotFoundError,
)
from portfolio_tracker.application.contracts.dtos import (
    ReportInstrumentDto,
    ReportTransactionDto,
)
from portfolio_tracker.application.fx import FxService
from portfolio_tracker.application.institution import (
    InstitutionClient,
    InstitutionClientError,
    InstitutionReportParser,
    InstitutionReportParserError,
)
from portfolio_tracker.application.market_data import MarketDataService
from portfolio_tracker.application.persistence import UnitOfWork
from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.institution import Credentials
from portfolio_tracker.domain.instrument import (
    Instrument,
    InstrumentBaseData,
    InstrumentType,
    create_instrument,
)
from portfolio_tracker.domain.shared import Money
from portfolio_tracker.domain.transaction import Transaction

from .exceptions import FetchReportError, ParseReportError


class SyncService:
    def __init__(
        self,
        uow: UnitOfWork,
        fx_service: FxService,
        market_data_service: MarketDataService,
        client_factory: Callable[[str, Credentials], InstitutionClient[Credentials]],
        parser_factory: Callable[[str, str], InstitutionReportParser],
    ):
        self._uow = uow
        self._fx_service = fx_service
        self._market_data_service = market_data_service
        self._client_factory = client_factory
        self._parser_factory = parser_factory

    def import_(
        self,
        report_path: Path,
        institution_account_id: str,
        asset_account_ids: set[str] | None = None,
    ) -> None:
        institution_account = self._get_institution_account(institution_account_id)
        report: Iterator[str] = report_path.open("r", encoding="utf-8")
        self._process_report(institution_account, report, asset_account_ids)

    def sync(
        self,
        user_id: str,
        institution_account_ids: set[str] | None = None,
        asset_account_ids: set[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        restore: bool = False,
    ) -> None:
        if institution_account_ids and asset_account_ids:
            raise ValueError(
                "Parameters 'institution_account_ids' and 'asset_account_ids' are mutually exclusive."
            )

        with self._uow as uow:
            if asset_account_ids:
                asset_accounts = uow.accounts.get_asset_accounts_by_ids(
                    asset_account_ids
                )
                institution_account_ids = {
                    asset_account.institution_account_id
                    for asset_account in asset_accounts
                }

            if institution_account_ids:
                institution_accounts = uow.accounts.get_institution_accounts_by_ids(
                    institution_account_ids
                )

            else:
                institution_accounts = uow.accounts.get_institution_accounts_by_user_id(
                    user_id
                )

        results = asyncio.run(
            self._sync_institution_accounts(
                institution_accounts, start, end, restore
            )
        )

        transaction_dates: set[date] = set()

        for institution_account, report in results:
            report_transaction_dates = self._process_report(
                institution_account, report, asset_account_ids
            )
            transaction_dates.update(report_transaction_dates)

        self.sync_fx_rates(user_id, transaction_dates)
        self.sync_stock_splits(new_only=True)

    async def _sync_institution_accounts(
        self,
        institution_accounts: list[InstitutionAccount],
        start: datetime | None = None,
        end: datetime | None = None,
        restore: bool = False,
    ) -> list[tuple[InstitutionAccount, Iterator[str]]]:
        tasks = [
            self._sync_institution_account(
                institution_account, start, end, restore
            )
            for institution_account in institution_accounts
        ]
        return await asyncio.gather(*tasks)

    async def _sync_institution_account(
        self,
        institution_account: InstitutionAccount,
        start: datetime | None = None,
        end: datetime | None = None,
        restore: bool = False,
    ) -> tuple[InstitutionAccount, Iterator[str]]:
        if restore:
            start = datetime.combine(
                institution_account.created_on,
                time.min,
                tzinfo=timezone.utc,
            )
            end = institution_account.last_synced_at

        else:
            start = start or institution_account.last_synced_at
            end = end or datetime.now(tz=timezone.utc)

        credentials = self._get_credentials(institution_account.id)
        client = self._client_factory(institution_account.institution_id, credentials)

        try:
            report = await client.fetch_report(start, end)

        except InstitutionClientError as error:
            raise FetchReportError(
                institution_account.id, institution_account.name
            ) from error
        
        return institution_account, report

    def _process_report(
        self,
        institution_account: InstitutionAccount,
        report: Iterator[str],
        required_asset_account_ids: set[str] | None = None,
    ) -> set[date]:
        required_asset_account_ids = required_asset_account_ids or set()

        parser = self._parser_factory(
            institution_account.institution_id, institution_account.id
        )

        try:
            report_transactions = parser.parse_report(report)

        except InstitutionReportParserError as error:
            raise ParseReportError(
                institution_account.id, institution_account.name
            ) from error

        transaction_dates: set[date] = set()
        instrument_ids: set[str] = set()
        asset_account_id_by_external_id: dict[str, str] = {}
    
        with self._uow as uow:
            ignored_external_ids = (
                uow.accounts.get_deactivated_asset_account_external_ids(
                    institution_account.id
                )
            )

            required_external_ids: set[str] = set()

            for required_asset_account_id in required_asset_account_ids:
                asset_account = uow.accounts.get_asset_account_by_id(
                    required_asset_account_id
                )
                if asset_account:
                    required_external_ids.add(asset_account.external_id)
                    asset_account_id_by_external_id[asset_account.id] = (
                        asset_account.external_id
                    )

            ignored_external_ids -= required_asset_account_ids

            for report_transaction in report_transactions:
                external_id = report_transaction.external_asset_account_id

                if external_id in ignored_external_ids:
                    continue

                if (
                    required_asset_account_ids
                    and external_id not in required_asset_account_ids
                ):
                    continue

                transaction_dates.add(report_transaction.executed_at.date())

                asset_account_id = asset_account_id_by_external_id.get(external_id)
                if not asset_account_id:
                    asset_account = uow.accounts.get_asset_account_by_external_id(
                        institution_account_id=institution_account.id,
                        external_id=external_id,
                    )
                    if not asset_account:
                        asset_account = AssetAccount(
                            institution_account_id=institution_account.id,
                            external_id=external_id,
                            name=f"{institution_account.name} asset account [{external_id}]",
                            is_active=True,
                        )
                        uow.accounts.add_asset_account(asset_account)

                    asset_account_id = asset_account.id
                    asset_account_id_by_external_id[external_id] = asset_account_id

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

            uow.accounts.update_institution_account(institution_account)
            uow.commit()
        
        return transaction_dates

    def sync_fx_rates(
        self,
        user_id: str,
        transaction_dates: set[date] | None = None,
    ) -> None:
        with self._uow as uow:
            if not transaction_dates:
                asset_accounts = uow.accounts.get_asset_accounts_by_user_id(user_id)
                transaction_dates = uow.transactions.get_distinct_dates(
                    filter_=FilterNode(
                        "asset_account_id", Operator.IN, {asset_account.id for asset_account in asset_accounts})
                )

            rates_dates = uow.fx_rates.get_distinct_dates()

        missing_dates = transaction_dates - rates_dates
        if not missing_dates:
            return

        rates_stream = self._fx_service.get_rates_series(
            from_date=min(missing_dates),
            to_date=max(missing_dates),
        )

        with self._uow as uow:
            for rates in rates_stream:
                uow.fx_rates.ensure(rates)

            uow.commit()

    def sync_stock_splits(
        self, new_only: bool = False,
        last_synced_before: timedelta = timedelta(days=1)
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        if new_only:
            filter_=FilterNode("last_synced_at", Operator.EQ, None)
        else:
            filter_=FilterNode("last_synced_at", Operator.LT, now - last_synced_before)
        
        with self._uow as uow:
            instruments_metadata = uow.instruments.get_metadata(filter_=filter_)

        splits_list = self._market_data_service.get_stock_splits(instruments_metadata)
        with self._uow as uow:
            for splits in splits_list:
                uow.market_data.ensure_stock_splits(splits)

            uow.instruments.update_last_synced_at(
                last_synced_at=now,
                instrument_ids={metadata.id for metadata in instruments_metadata}
            )
            uow.commit()

    def _get_institution_account(self, account_id: str) -> InstitutionAccount:
        with self._uow as uow:
            institution_account = uow.accounts.get_institution_account_by_id(account_id)
            if not institution_account:
                raise InstitutionAccountNotFoundError(account_id)

            return institution_account

    def _get_credentials(self, account_id: str) -> Credentials:
        with self._uow as uow:
            credentials = uow.credentials.retrieve(account_id)
            if not credentials:
                raise CredentialsNotFoundError(account_id)

            return credentials

    def _resolve_transaction(
        self,
        report_transaction: ReportTransactionDto,
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
            executed_at=report_transaction.executed_at,
            asset_account_id=asset_account_id,
            type=report_transaction.type,
            instrument_id=main_instrument_id,
            quantity=report_transaction.quantity,
            price=Money(
                report_transaction.price.amount,
                report_transaction.price.currency,
            ),
            fee=Money(report_transaction.fee.amount, report_transaction.fee.currency),
            tax=Money(report_transaction.tax.amount, report_transaction.tax.currency),
            cash_impact=Money(
                report_transaction.cash_impact.amount,
                report_transaction.cash_impact.currency,
            ),
            correlation_id=report_transaction.correlation_id,
        )

        return transaction, instruments

    def _resolve_instrument(
        self, report_instrument: ReportInstrumentDto, institution_id: str
    ) -> tuple[Instrument, list[Instrument]]:
        base_data: InstrumentBaseData = {
            "name": report_instrument.name,
            "symbol": report_instrument.symbol,
            "exchange": report_instrument.exchange,
            "currency": report_instrument.currency,
            "last_synced_at": None,
            "_id": None,
            "_checksum": None,
        }
        details = report_instrument.details

        underlying_instruments: list[Instrument] = []

        if report_instrument.type.is_derivative:
            underlying_instrument, other_instruments = self._resolve_instrument(
                details["underlying_instrument"], institution_id
            )
            underlying_instruments = [underlying_instrument] + other_instruments

            details["underlying_instrument_id"] = underlying_instrument.id
            details["asset_class"] = underlying_instrument.asset_class
            if report_instrument.type == InstrumentType.CFD:
                details["institution_id"] = institution_id

        main_instrument = create_instrument(report_instrument.type, base_data, details)

        return main_instrument, underlying_instruments
