from collections.abc import Iterable

from portfolio_tracker.application.fx import FxService
from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.market_data import MarketDataService
from portfolio_tracker.application.persistence import (
    StorageConnectionFactory,
    UserScopedUnitOfWork,
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
from portfolio_tracker.domain.account import AssetAccount
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
        return self._view_builder.build_cash_balance_row_views(
            portfolio_views=self.get_portfolios(user_id, query)
        )

    def get_positions(
        self, user_id: str, query: GetPortfoliosQuery
    ) -> list[PositionRowView]:
        return list(
            self._view_builder.build_position_row_views(
                portfolio_views=self.get_portfolios(user_id, query)
            ).values()
        )

    def get_portfolios(
        self, user_id: str, query: GetPortfoliosQuery
    ) -> list[ValuedPortfolioView]:
        institutions, institution_connections, accounts, instruments, portfolios = (
            self._build_portfolios(user_id, query)
        )
        valued_portfolios = self._evaluate_portfolios(portfolios, instruments)
        return list(
            self._view_builder.build_valued_portfolio_views(
                institutions,
                institution_connections,
                accounts,
                instruments,
                valued_portfolios,
            ).values()
        )

    def get_portfolio_valuations(
        self, user_id: str, query: GetPortfoliosQuery
    ) -> dict[str | None, PortfolioValuationView]:
        _, _, _, instruments, portfolios = self._build_portfolios(user_id, query)
        portfolio_valuations = self._get_portfolio_valuations(portfolios, instruments)
        return self._view_builder.build_portfolio_valuation_views(portfolio_valuations)

    def _build_portfolios(
        self,
        user_id: str,
        query: GetPortfoliosQuery,
    ) -> tuple[
        list[Institution],
        list[InstitutionConnection],
        list[AssetAccount],
        list[Instrument],
        list[Portfolio],
    ]:
        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            transactions: Iterable[Transaction] = uow.transactions.get(
                institution_connection_ids=query.institution_connection_ids,
                account_ids=query.account_ids,
                filter_=query.filter,
                sorts=[self._REQUIRED_TRANSACTION_SORT],
            )
            instrument_ids = uow.transactions.get_distinct_instrument_ids(
                institution_connection_ids=query.institution_connection_ids,
                account_ids=query.account_ids,
                filter_=query.filter,
            )
            splits_list = uow.market_data.get_stock_splits_by_instrument_ids(
                instrument_ids
            )
            adjustied_transactions = self._transaction_adjuster.adjust(
                transactions, splits_list
            )

            transaction_dates = uow.transactions.get_distinct_dates(
                institution_connection_ids=query.institution_connection_ids,
                account_ids=query.account_ids,
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
                portfolios, query.scope, uow.account_map
            )
            instruments = uow.instruments.get_by_ids(
                instrument_ids={
                    instrument_id
                    for portfolio in portfolios
                    for instrument_id in portfolio.instrument_ids
                }
            )
            institutions, institution_connections, accounts = (
                self._get_portfolio_accounts(uow, portfolios)
            )
            return (
                institutions,
                institution_connections,
                accounts,
                instruments,
                portfolios,
            )

    def _get_portfolio_accounts(
        self,
        uow: UserScopedUnitOfWork,
        portfolios: list[Portfolio],
    ) -> tuple[list[Institution], list[InstitutionConnection], list[AssetAccount]]:
        institution_connection_ids: set[str] = set()
        account_ids: set[str] = set()

        for portfolio in portfolios:
            if portfolio.scope.type == ScopeType.GLOBAL:
                continue

            assert portfolio.scope.id is not None
            if portfolio.scope.type == ScopeType.INSTITUTION:
                institution_connection_ids.add(portfolio.scope.id)

            elif portfolio.scope.type == ScopeType.ACCOUNT:
                account_ids.add(portfolio.scope.id)

        accounts = uow.accounts.get_by_ids(account_ids)
        institution_connections = uow.institution_connections.get_by_ids(
            institution_connection_ids
        )
        institutions = [
            self._institution_registry.get_institution(
                institution_connection.institution_id
            )
            for institution_connection in institution_connections
        ]

        return institutions, institution_connections, accounts

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
