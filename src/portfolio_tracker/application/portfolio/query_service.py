from collections.abc import Iterable

from filterutils import Filter

from portfolio_tracker.application.contracts.dto_assembler import DtoAssembler
from portfolio_tracker.application.contracts.dtos import (
    PortfolioDto,
    PortfolioValuationDto,
    ValuedPortfolioDto,
)
from portfolio_tracker.application.contracts.queries import (
    GetPortfoliosQuery,
    OutputType,
)
from portfolio_tracker.application.fx import FxService
from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.market_data import MarketDataService
from portfolio_tracker.application.persistence import (
    AccountRepository,
    FxRatesRepository,
    InstrumentRepository,
    MarketDataRepository,
    TransactionRepository,
    UnitOfWork,
)
from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.instrument import Instrument
from portfolio_tracker.domain.portfolio import (
    ConsolidationScope,
    Portfolio,
    PortfolioBuilder,
    PortfolioEvaluator,
    PortfolioValuation,
)
from portfolio_tracker.domain.transaction import Transaction, TransactionAdjuster


class PortfolioQueryService:
    def __init__(
        self,
        institution_registry: InstitutionRegistry,
        uow: UnitOfWork,
        transaction_adjuster: TransactionAdjuster,
        portfolio_builder: PortfolioBuilder,
        portfolio_evaluator: PortfolioEvaluator,
        fx_service: FxService,
        market_data_service: MarketDataService,
    ) -> None:
        self._institution_registry = institution_registry
        self._uow = uow
        self._market_data_service = market_data_service
        self._fx_service = fx_service
        self._transaction_adjuster = transaction_adjuster
        self._portfolio_builder = portfolio_builder
        self._portfolio_evaluator = portfolio_evaluator

    def execute(
        self, query: GetPortfoliosQuery
    ) -> (
        list[PortfolioDto]
        | dict[str | None, PortfolioValuationDto]
        | list[ValuedPortfolioDto]
    ):
        with self._uow as uow:
            transactions: Iterable[Transaction] = uow.transactions.get(
                filter_=query.filter,
                order_by=[("executed_at", "ASC")],
            )
            transactions = self._adjust_transactions(
                transactions,
                uow.transactions,
                uow.market_data,
                query.filter,
            )
            portfolios = self._calculate_portfolios(
                transactions,
                query.reporting_currency,
                uow.transactions,
                uow.fx_rates,
                query.filter,
            )
            account_id_map = self._get_account_id_map(portfolios, uow.accounts)
            if query.scope != ConsolidationScope.ASSET_ACCOUNT:
                portfolios = self._consolidate_portfolios(
                    portfolios, query.scope, account_id_map
                )

            asset_accounts, institution_accounts = self._get_portfolio_accounts(
                account_id_map,
                uow.accounts,
                query.scope,
            )
            instruments = self._get_portfolio_instruments(portfolios, uow.instruments)

        institutions = [
            self._institution_registry.get(institution_account.institution_id)
            for institution_account in institution_accounts
        ]

        if query.output_type == OutputType.PORTFOLIO:
            return DtoAssembler.assemble_portfolios(
                institutions,
                institution_accounts,
                asset_accounts,
                instruments,
                portfolios,
            )

        portfolio_valuations = self._value_portfolios(portfolios, instruments)

        if query.output_type == OutputType.PORTFOLIO_VALUATION:
            return DtoAssembler.assemble_portfolio_valuations(portfolio_valuations)

        if query.output_type == OutputType.VALUED_PORTFOLIO:
            return DtoAssembler.assemble_valued_portfolios(
                institutions,
                institution_accounts,
                asset_accounts,
                instruments,
                portfolios,
                portfolio_valuations,
            )

        raise ValueError(f"Unexpected output type: {query.output_type}")

    def _adjust_transactions(
        self,
        transactions: Iterable[Transaction],
        transaction_repository: TransactionRepository,
        market_data_repository: MarketDataRepository,
        filter_: Filter | None = None,
    ) -> Iterable[Transaction]:
        instrument_ids = transaction_repository.get_distinct_instrument_ids(filter_)
        splits_list = market_data_repository.get_stock_splits_by_instrument_ids(
            instrument_ids
        )
        return self._transaction_adjuster.adjust(transactions, splits_list)

    def _calculate_portfolios(
        self,
        transactions: Iterable[Transaction],
        reporting_currency: str,
        transaction_repository: TransactionRepository,
        fx_rates_repository: FxRatesRepository,
        filter_: Filter | None = None,
    ) -> list[Portfolio]:
        dates = transaction_repository.get_distinct_dates(filter_)
        rates_by_date = fx_rates_repository.get_required_rates_by_date_map(
            dates,
        )
        return self._portfolio_builder.build(
            transactions, rates_by_date, reporting_currency
        )

    def _get_account_id_map(
        self,
        portfolios: list[Portfolio],
        account_repository: AccountRepository,
    ) -> dict[str, str]:
        asset_account_ids = {
            portfolio.account_id for portfolio in portfolios if portfolio.account_id
        }
        return account_repository.get_institution_account_id_by_asset_account_id_map(
            asset_account_ids
        )

    def _consolidate_portfolios(
        self,
        portfolios: list[Portfolio],
        scope: ConsolidationScope,
        account_id_map: dict[str, str],
    ) -> list[Portfolio]:
        return self._portfolio_builder.consolidate(portfolios, scope, account_id_map)

    def _get_portfolio_instruments(
        self,
        portfolios: list[Portfolio],
        instrument_repository: InstrumentRepository,
    ) -> list[Instrument]:
        instrument_ids = {
            instrument_id
            for portfolio in portfolios
            for instrument_id in portfolio.instrument_ids
        }
        return instrument_repository.get_by_ids(instrument_ids)

    def _get_portfolio_accounts(
        self,
        account_id_map: dict[str, str],
        account_repository: AccountRepository,
        scope: ConsolidationScope,
    ) -> tuple[list[AssetAccount], list[InstitutionAccount]]:
        asset_accounts: list[AssetAccount] = []
        institution_accounts: list[InstitutionAccount] = []

        if scope == ConsolidationScope.ASSET_ACCOUNT:
            asset_accounts = account_repository.get_asset_accounts_by_ids(
                set(account_id_map.keys())
            )

        if scope <= ConsolidationScope.INSTITUTION_ACCOUNT:
            institution_accounts = account_repository.get_institution_accounts_by_ids(
                set(account_id_map.values())
            )

        return asset_accounts, institution_accounts

    def _value_portfolios(
        self,
        portfolios: list[Portfolio],
        instruments: list[Instrument],
    ) -> dict[str | None, PortfolioValuation]:
        instruments_metadata = [instrument.metadata for instrument in instruments]
        native_market_prices = self._market_data_service.get_spot_prices(
            instruments_metadata
        )
        spot_rates = self._fx_service.get_spot_rates()
        return {
            portfolio.account_id: self._portfolio_evaluator.evaluate(
                portfolio,
                instruments_metadata,
                native_market_prices,
                spot_rates,
            )
            for portfolio in portfolios
        }
