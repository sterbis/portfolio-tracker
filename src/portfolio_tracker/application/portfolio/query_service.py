from collections.abc import Iterable

from portfolio_tracker.application.fx import FxService
from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.market_data import MarketDataService
from portfolio_tracker.application.persistence import (
    StorageConnectionFactory,
    UserScopedUnitOfWork,
)
from portfolio_tracker.application.shared.filter import FilterMapper, FilterSplitter
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.application.shared.service import QueryService
from portfolio_tracker.application.views import (
    PortfolioValuationView,
    PortfolioView,
    ValuedPortfolioView,
    ViewBuilder,
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
from portfolio_tracker.domain.transaction import (
    Transaction,
    TransactionAdjuster,
    TransactionConverter,
)

from .queries import GetPortfoliosQuery


class PortfolioQueryService(QueryService):
    REQUIRED_TRANSACTION_SORT: Sort = Sort("executed_at", Transaction, "ASC")

    def __init__(
        self,
        storage_connection_factory: StorageConnectionFactory,
        filter_mapper: FilterMapper,
        filter_splitter: FilterSplitter,
        view_builder: ViewBuilder,
        institution_registry: InstitutionRegistry,
        transaction_adjuster: TransactionAdjuster,
        portfolio_builder: PortfolioBuilder,
        portfolio_evaluator: PortfolioEvaluator,
        fx_service: FxService,
        market_data_service: MarketDataService,
    ) -> None:
        super().__init__(storage_connection_factory, filter_mapper, filter_splitter, view_builder)
        self._institution_registry = institution_registry
        self._market_data_service = market_data_service
        self._fx_service = fx_service
        self._transaction_adjuster = transaction_adjuster
        self._portfolio_builder = portfolio_builder
        self._portfolio_evaluator = portfolio_evaluator

    def get_portfolios(
        self, user_id: str, query: GetPortfoliosQuery
    ) -> list[PortfolioView]:
        institution_accounts, asset_accounts, instruments, portfolios = (
            self._get_portfolios(user_id, query)
        )
        institutions = [
            self._institution_registry.get_institution(
                institution_account.institution_id
            )
            for institution_account in institution_accounts
        ]
        return self._view_builder.build_portfolio_views(
            institutions,
            institution_accounts,
            asset_accounts,
            instruments,
            portfolios,
        )

    def get_portfolio_valuations(
        self, user_id: str, query: GetPortfoliosQuery
    ) -> dict[str | None, PortfolioValuationView]:
        _, _, instruments, portfolios = self._get_portfolios(user_id, query)
        portfolio_valuations = self._value_portfolios(portfolios, instruments)
        return self._view_builder.build_portfolio_valuation_views(portfolio_valuations)

    def get_valued_portfolios(
        self, user_id: str, query: GetPortfoliosQuery
    ) -> list[ValuedPortfolioView]:
        institution_accounts, asset_accounts, instruments, portfolios = (
            self._get_portfolios(user_id, query)
        )
        institutions = [
            self._institution_registry.get_institution(
                institution_account.institution_id
            )
            for institution_account in institution_accounts
        ]
        portfolio_valuations = self._value_portfolios(portfolios, instruments)
        return self._view_builder.build_valued_portfolio_views(
            institutions,
            institution_accounts,
            asset_accounts,
            instruments,
            portfolios,
            portfolio_valuations,
        )

    def _get_portfolios(
        self,
        user_id: str,
        query: GetPortfoliosQuery,
    ) -> tuple[
        list[InstitutionAccount],
        list[AssetAccount],
        list[Instrument],
        list[Portfolio],
    ]:
        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            transactions: Iterable[Transaction] = uow.transactions.get(
                institution_account_ids=query.institution_account_ids,
                asset_account_ids=query.asset_account_ids,
                filter_=query.filter,
                sorts=[self.REQUIRED_TRANSACTION_SORT],
            )
            instrument_ids = uow.transactions.get_distinct_instrument_ids(
                institution_account_ids=query.institution_account_ids,
                asset_account_ids=query.asset_account_ids,
                filter_=query.filter,
            )
            splits_list = uow.market_data.get_stock_splits_by_instrument_ids(
                instrument_ids
            )
            adjustied_transactions = self._transaction_adjuster.adjust(
                transactions, splits_list
            )

            transaction_dates = uow.transactions.get_distinct_dates(
                institution_account_ids=query.institution_account_ids,
                asset_account_ids=query.asset_account_ids,
                filter_=query.filter,
            )
            rates_by_date = uow.fx_rates.get_required_rates_by_date_map(
                transaction_dates,
            )
            converter = TransactionConverter(rates_by_date)
            converted_transactions = converter.convert_many(
                adjustied_transactions, query.reporting_currency
            )

            portfolios = self._portfolio_builder.build(
                converted_transactions, query.reporting_currency
            )
            portfolios = self._portfolio_builder.consolidate(
                portfolios, query.scope, uow.accounts_map
            )
            instruments = uow.instruments.get_by_ids(
                instrument_ids={
                    instrument_id
                    for portfolio in portfolios
                    for instrument_id in portfolio.instrument_ids
                }
            )
            institution_accounts, asset_accounts = self._get_portfolio_accounts(
                uow, portfolios
            )
            return institution_accounts, asset_accounts, instruments, portfolios

    def _get_portfolio_accounts(
        self,
        uow: UserScopedUnitOfWork,
        portfolios: list[Portfolio],
    ) -> tuple[list[InstitutionAccount], list[AssetAccount]]:
        institution_account_ids: set[str] = set()
        asset_account_ids: set[str] = set()

        for portfolio in portfolios:
            if portfolio.scope == ConsolidationScope.GLOBAL:
                continue

            assert portfolio.account_id is not None
            if portfolio.scope == ConsolidationScope.INSTITUTION_ACCOUNT:
                institution_account_ids.add(portfolio.account_id)

            elif portfolio.scope == ConsolidationScope.ASSET_ACCOUNT:
                asset_account_ids.add(portfolio.account_id)

        institution_accounts = uow.accounts.get_institution_accounts_by_ids(
            institution_account_ids
        )
        asset_accounts = uow.accounts.get_asset_accounts_by_ids(asset_account_ids)

        return institution_accounts, asset_accounts

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
