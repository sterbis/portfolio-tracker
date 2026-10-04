from collections.abc import Iterable

from filterutils import Filter, FilterNode, FilterTree, Operator

from portfolio_tracker.application.fx import FxService
from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.market_data import MarketDataService
from portfolio_tracker.application.persistence import (
    ReadUnitOfWork,
    StorageReadConnectionFactory,
)
from portfolio_tracker.application.shared.errors import (
    FxClientError,
    MarketDataClientError,
)
from portfolio_tracker.application.shared.filter import FilterMapper, FilterSplitter
from portfolio_tracker.application.shared.service import QueryService
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.application.views import (
    CashBalanceRowView,
    PortfolioValuationView,
    PositionRowView,
    ValuedPortfolioView,
    ViewBuilder,
)
from portfolio_tracker.domain.account import AccountMap, AssetAccount
from portfolio_tracker.domain.institution import Institution, InstitutionConnection
from portfolio_tracker.domain.instrument import Instrument
from portfolio_tracker.domain.portfolio import (
    Portfolio,
    PortfolioBuilder,
    PortfolioEvaluator,
    PortfolioValuation,
    ScopeType,
    ValuedPortfolio,
)
from portfolio_tracker.domain.transaction import (
    Transaction,
    TransactionAdjuster,
    TransactionConverter,
)

from .queries import GetPortfoliosQuery


class PortfolioQueryService(QueryService):
    _REQUIRED_TRANSACTION_SORT: Sort = Sort("executed_at", Transaction)

    def __init__(
        self,
        storage_connection_factory: StorageReadConnectionFactory,
        filter_mapper: FilterMapper,
        filter_splitter: FilterSplitter,
        view_builder: ViewBuilder,
        institution_registry: InstitutionRegistry,
        fx_service: FxService,
        market_data_service: MarketDataService,
        transaction_adjuster: TransactionAdjuster,
        portfolio_builder: PortfolioBuilder,
        portfolio_evaluator: PortfolioEvaluator,
    ) -> None:
        super().__init__(
            storage_connection_factory, filter_mapper, filter_splitter, view_builder
        )
        self._institution_registry = institution_registry
        self._market_data_service = market_data_service
        self._fx_service = fx_service
        self._transaction_adjuster = transaction_adjuster
        self._portfolio_builder = portfolio_builder
        self._portfolio_evaluator = portfolio_evaluator

    def get_cash_balances(
        self, user_id: str, query: GetPortfoliosQuery
    ) -> list[CashBalanceRowView]:
        views = self._view_builder.build_cash_balance_row_views(
            portfolio_views=self.get_portfolios(user_id, query)
        )
        return self._apply_view_options(views, sorts=query.sorts)

    def get_positions(
        self, user_id: str, query: GetPortfoliosQuery
    ) -> list[PositionRowView]:
        _, memory_filter = self._resolve_filters(query.filter)
        views = self._view_builder.build_position_row_views(
            portfolio_views=self.get_portfolios(user_id, query)
        )
        if memory_filter:
            views = list(memory_filter.apply(views))

        return self._apply_view_options(views, sorts=query.sorts)

    def get_portfolios(
        self, user_id: str, query: GetPortfoliosQuery
    ) -> list[ValuedPortfolioView]:
        repository_filter, _ = self._resolve_filters(query.filter)
        institutions, connections, accounts, instruments, portfolios = (
            self._build_portfolios(user_id, query, repository_filter)
        )
        valued_portfolios = self._evaluate_portfolios(portfolios, instruments)
        return list(
            self._view_builder.build_valued_portfolio_views(
                institutions,
                connections,
                accounts,
                instruments,
                valued_portfolios,
            ).values()
        )

    def get_portfolio_valuations(
        self, user_id: str, query: GetPortfoliosQuery
    ) -> dict[str | None, PortfolioValuationView]:
        repository_filter, _ = self._resolve_filters(query.filter)
        _, _, _, instruments, portfolios = self._build_portfolios(
            user_id, query, repository_filter
        )
        portfolio_valuations = self._get_portfolio_valuations(portfolios, instruments)
        return self._view_builder.build_portfolio_valuation_views(portfolio_valuations)

    def _build_portfolios(
        self,
        user_id: str,
        query: GetPortfoliosQuery,
        filter_: Filter | None,
    ) -> tuple[
        list[Institution],
        list[InstitutionConnection],
        list[AssetAccount],
        list[Instrument],
        list[Portfolio],
    ]:
        with self._unit_of_work(user_id) as uow:
            account_map = uow.accounts.get_user_account_map()
            required_account_ids = account_map.resolve_account_ids(
                query.connection_ids, query.account_ids
            )

            transactions: Iterable[Transaction] = uow.transactions.get(
                filter_=FilterTree.and_combine(
                    filter_,
                    (
                        FilterNode(
                            "account_id", Operator.IN, required_account_ids, Transaction
                        )
                        if required_account_ids
                        else None
                    ),
                ),
                sorts=[self._REQUIRED_TRANSACTION_SORT],
            )
            instrument_ids = uow.transactions.get_distinct_instrument_ids(
                filter_=filter_
            )
            splits_list = uow.market_data.get_stock_splits_by_instrument_ids(
                instrument_ids
            )
            adjustied_transactions = self._transaction_adjuster.adjust(
                transactions, splits_list
            )

            transaction_dates = uow.transactions.get_distinct_dates(filter_=filter_)
            rates_by_date = uow.fx_rates.get_by_dates_required(
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
                portfolios, query.scope, account_map
            )

            instruments = uow.instruments.get_by_ids(
                instrument_ids={
                    instrument_id
                    for portfolio in portfolios
                    for instrument_id in portfolio.instrument_ids
                }
            )
            institutions, connections, accounts = self._get_portfolio_scopes(
                uow, portfolios, account_map
            )
            return (
                institutions,
                connections,
                accounts,
                instruments,
                portfolios,
            )

    def _get_portfolio_scopes(
        self,
        uow: ReadUnitOfWork,
        portfolios: list[Portfolio],
        account_map: AccountMap,
    ) -> tuple[list[Institution], list[InstitutionConnection], list[AssetAccount]]:
        connection_ids: set[str] = set()
        account_ids: set[str] = set()

        for portfolio in portfolios:
            if portfolio.scope.type == ScopeType.GLOBAL:
                continue

            assert portfolio.scope.id is not None
            if portfolio.scope.type == ScopeType.INSTITUTION:
                connection_ids.add(portfolio.scope.id)

            elif portfolio.scope.type == ScopeType.ACCOUNT:
                account_ids.add(portfolio.scope.id)
                connection_ids.add(
                    account_map.account_id_to_connection_id[portfolio.scope.id]
                )

        accounts = uow.accounts.get_by_ids(account_ids)
        connections = uow.institution_connections.get_by_ids(connection_ids)
        institutions = [
            self._institution_registry.get_institution(connection.institution_id)
            for connection in connections
        ]

        return institutions, connections, accounts

    def _get_portfolio_valuations(
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
            portfolio.scope.id: self._portfolio_evaluator.get_valuation(
                portfolio,
                instruments_metadata,
                native_market_prices,
                spot_rates,
            )
            for portfolio in portfolios
        }

    def _evaluate_portfolios(
        self,
        portfolios: list[Portfolio],
        instruments: list[Instrument],
    ) -> list[ValuedPortfolio]:
        try:
            valuations = self._get_portfolio_valuations(portfolios, instruments)
        except FxClientError, MarketDataClientError:
            valuations = {}

        return [
            ValuedPortfolio(
                portfolio=portfolio, valuation=valuations.get(portfolio.scope.id)
            )
            for portfolio in portfolios
        ]
