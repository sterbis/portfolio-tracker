from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from portfolio_tracker.application.contracts.dtos import (
    ReportInstrumentDto,
    ReportTransactionDto,
)
from portfolio_tracker.application.fx import FxService
from portfolio_tracker.application.institution import (
    InstitutionClient,
    InstitutionReportParser,
)
from portfolio_tracker.application.market_data import MarketDataService
from portfolio_tracker.application.persistence import UnitOfWork
from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.institution import Credentials
from portfolio_tracker.domain.instrument import (
    Instrument,
    InstrumentBaseData,
    InstrumentMetadata,
    InstrumentType,
    create_instrument,
)
from portfolio_tracker.domain.shared import Money
from portfolio_tracker.domain.transaction import Transaction


class SyncService:
    def __init__(
        self,
        uow: UnitOfWork,
        fx_service: FxService,
        market_data_service: MarketDataService,
        client_factory: Callable[[str, Credentials], InstitutionClient[Credentials]],
        parser_factory: Callable[[str], InstitutionReportParser],
    ):
        self._uow = uow
        self._fx_service = fx_service
        self._market_data_service = market_data_service
        self._client_factory = client_factory
        self._parser_factory = parser_factory

    def sync_institution_account_from_api(self, institution_account_id: str) -> None:
        institution_account, credentials = (
            self._get_institution_account_and_credentials(institution_account_id)
        )

        client = self._client_factory(institution_account.institution_id, credentials)
        report = client.fetch_report(
            start=institution_account.last_synced_at,
            end=datetime.now(tz=timezone.utc),
        )

        updated_institution_account = institution_account.with_last_synced_at(
            datetime.now(timezone.utc)
        )

        self._sync_institution_account_from_report(
            updated_institution_account,
            report,
            institution_account_updated=True,
        )

    def sync_institution_account_from_report_file(
        self, institution_account_id: str, report_path: Path
    ) -> None:
        with report_path.open("r") as report_file:
            report = report_file.read()

        with self._uow as uow:
            institution_account = uow.accounts.get_institution_account_by_id(
                institution_account_id
            )
            if not institution_account:
                raise ValueError(
                    f"Institution account {institution_account_id} not found."
                )

        self._sync_institution_account_from_report(
            institution_account, report
        )

    def _sync_institution_account_from_report(
        self,
        institution_account: InstitutionAccount,
        report: str,
        institution_account_updated: bool = False,
    ) -> None:
        parser = self._parser_factory(institution_account.institution_id)
        parsed_report = parser.parse_report(report)

        external_asset_account_ids: set[str] = set()
        transaction_dates: set[date] = set()
        instrument_metadata_by_id: dict[str, InstrumentMetadata] = {}

        for report_transaction in parsed_report.transactions:
            external_asset_account_ids.add(report_transaction.external_asset_account_id)
            transaction_dates.add(report_transaction.executed_at.date())

        with self._uow as uow:
            asset_account_id_by_external_id: dict[str, str] = {}

            for external_id in external_asset_account_ids:
                asset_account = uow.accounts.get_asset_account_by_external_id(
                    institution_account_id=institution_account.id,
                    external_id=external_id,
                )
                if not asset_account:
                    asset_account = AssetAccount(
                        institution_account_id=institution_account.id,
                        external_id=external_id,
                        name=f"Discovered {institution_account.name} asset account ({external_id})",
                    )
                    uow.accounts.add_asset_account(asset_account)

                asset_account_id_by_external_id[external_id] = asset_account.id

            for report_transaction in parsed_report.transactions:
                asset_account_id = asset_account_id_by_external_id[
                    report_transaction.external_asset_account_id
                ]
                transaction, instruments = self._resolve_transaction(
                    report_transaction,
                    asset_account_id,
                    institution_account.institution_id,
                )
                for instrument in reversed(instruments):
                    if instrument.id not in instrument_metadata_by_id:
                        instrument_metadata_by_id[instrument.id] = instrument.metadata
                        uow.instruments.ensure(instrument)

                uow.transactions.ensure(transaction)

            if institution_account_updated:
                uow.accounts.update_institution_account(institution_account)

            uow.commit()

        self._sync_fx_rates(transaction_dates)
        self._sync_stock_splits(instrument_metadata_by_id.values())

    def _sync_fx_rates(self, dates: set[date]) -> None:
        with self._uow as uow:
            existing_dates = uow.fx_rates.get_distinct_dates()

        missing_dates = dates - existing_dates
        if not missing_dates:
            return

        rates_list = self._fx_service.get_historical_rates(missing_dates)

        with self._uow as uow:
            for rates in rates_list:
                uow.fx_rates.ensure(rates)

            uow.commit()

    def _sync_stock_splits(
        self, instruments_metadata: Iterable[InstrumentMetadata]
    ) -> None:
        splits_list = self._market_data_service.get_stock_splits(instruments_metadata)
        with self._uow as uow:
            for splits in splits_list:
                uow.market_data.ensure_stock_splits(splits)

            uow.commit()

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

    def _get_institution_account_and_credentials(
        self, institution_account_id: str
    ) -> tuple[InstitutionAccount, Credentials]:
        with self._uow as uow:
            institution_account = uow.accounts.get_institution_account_by_id(
                institution_account_id
            )
            if not institution_account:
                raise ValueError(
                    f"Institution account {institution_account_id} not found."
                )

            credentials = uow.credentials.retrieve(institution_account.id)
            if not credentials:
                raise ValueError(
                    f"Credentials for institution account {institution_account.id} not found."
                )

            return institution_account, credentials
