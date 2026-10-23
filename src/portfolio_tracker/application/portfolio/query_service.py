from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from decimal import Decimal

from filterutils import FilterNode, Operator

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
from portfolio_tracker.application.shared.filter_mapper import FilterMapper
from portfolio_tracker.application.shared.service import QueryService
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.application.views import (
    CashBalanceRowView,
    MoneyView,
    PositionRowView,
    PositionRowTotalView,
    ValuedPortfolioView,
    ViewBuilder,
)
from portfolio_tracker.domain.account import AssetAccount
from portfolio_tracker.domain.institution import Institution, InstitutionConnection
from portfolio_tracker.domain.instrument import Instrument, InstrumentMetadata
from portfolio_tracker.domain.market_data import MarketData
from portfolio_tracker.domain.portfolio import (
    Portfolio,
    PortfolioBuilder,
    PortfolioValuation,
    PortfolioValuationEngine,
    ValuedPortfolio,
)
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.domain.transaction import (
    ConvertedTransaction,
    Transaction,
    TransactionAdjuster,
    TransactionConverter,
)

from .queries import (
    BuildPortfolioSnapshotQuery,
    GetPositionsQuery,
    GetCashBalancesQuery,
    GetPortfolioQuery,
    ViewPortfolioSnapshotQuery,
)


@dataclass(frozen=True, kw_only=True)
class PortfolioSnapshot:
    portfolios: tuple[Portfolio, ...]
    instruments: tuple[Instrument, ...]
    institutions: tuple[Institution, ...]
    connections: tuple[InstitutionConnection, ...]
    accounts: tuple[AssetAccount, ...]
    query: BuildPortfolioSnapshotQuery


@dataclass(frozen=True)
class PositionsResult:
    positions: tuple[PositionRowView, ...]
    totals: PositionRowTotalView


class PortfolioQueryService(QueryService):
    _REQUIRED_TRANSACTION_SORT: Sort = Sort("executed_at", Transaction)

    def __init__(
        self,
        storage_connection_factory: StorageReadConnectionFactory,
        filter_mapper: FilterMapper,
        view_builder: ViewBuilder,
        institution_registry: InstitutionRegistry,
        fx_service: FxService,
        market_data_service: MarketDataService,
        transaction_adjuster: TransactionAdjuster,
        portfolio_builder: PortfolioBuilder,
        portfolio_valuation_engine: PortfolioValuationEngine,
    ) -> None:
        super().__init__(storage_connection_factory, filter_mapper, view_builder)
        self._institution_registry = institution_registry
        self._market_data_service = market_data_service
        self._fx_service = fx_service
        self._transaction_adjuster = transaction_adjuster
        self._portfolio_builder = portfolio_builder
        self._portfolio_valuation_engine = portfolio_valuation_engine

    def get_cash_balances(
        self, user_id: str, query: GetCashBalancesQuery
    ) -> list[CashBalanceRowView]:
        views = self._view_builder.build_cash_balance_row_views(
            portfolio_views=self.get_portfolio(
                user_id,
                query=GetPortfolioQuery(
                    build=query.build,
                    view=query.view,
                ),
            )
        )
        return self._apply_query_options(views, query.view.options)

    def get_positions(self, user_id: str, query: GetPositionsQuery) -> PositionsResult:
        snapshot = self.build_snapshot(user_id, query.build)
        return self.positions_from_snapshot(snapshot, query.view)

    def positions_from_snapshot(
        self,
        snapshot: PortfolioSnapshot,
        query: ViewPortfolioSnapshotQuery,
        market_data: MarketData | None = None,
    ) -> PositionsResult:
        valued_portfolios = self._process_snapshot(snapshot, query, market_data)
        views = self._view_builder.build_position_row_views(
            snapshot.institutions,
            snapshot.connections,
            snapshot.accounts,
            snapshot.instruments,
            valued_portfolios,
        )
        views = self._apply_query_options(views, query.options)
        total_view = self._get_postitions_total(
            views, snapshot.query.reporting_currency
        )
        return PositionsResult(positions=tuple(views), totals=total_view)

    def _get_postitions_total(
        self, views: list[PositionRowView], reporting_currency: Currency
    ) -> PositionRowTotalView:
        cost_basis_amount = Decimal("0")
        market_value_amount = Decimal("0")
        portfolio_weight = Decimal("0")
        invested_capital_weight = Decimal("0")
        unrealized_pnl_amount = Decimal("0")

        for view in views:
            if view.valuation is None:
                continue

            cost_basis_amount += view.position.cost_basis.reporting.amount
            market_value_amount += view.valuation.market_value.reporting.amount
            portfolio_weight += view.valuation.portfolio_weight
            invested_capital_weight += view.valuation.invested_capital_weight
            unrealized_pnl_amount += view.valuation.unrealized_pnl.reporting.amount

        unrealized_pnl_percent = (
            unrealized_pnl_amount / cost_basis_amount
            if cost_basis_amount
            else Decimal("0")
        )
        return PositionRowTotalView(
            cost_basis=MoneyView(cost_basis_amount, reporting_currency),
            market_value=MoneyView(market_value_amount, reporting_currency),
            portfolio_weight=portfolio_weight,
            invested_capital_weight=invested_capital_weight,
            unrealized_pnl=MoneyView(unrealized_pnl_amount, reporting_currency),
            unrealized_pnl_percent=unrealized_pnl_percent,
        )

    def get_portfolio(
        self, user_id: str, query: GetPortfolioQuery
    ) -> list[ValuedPortfolioView]:
        snapshot = self.build_snapshot(user_id, query.build)
        valued_portfolios = self._process_snapshot(snapshot, query.view)
        return self._apply_query_options(
            views=self._view_builder.build_valued_portfolio_views(
                snapshot.institutions,
                snapshot.connections,
                snapshot.accounts,
                snapshot.instruments,
                valued_portfolios,
            ).values(),
            options=query.view.options,
        )

    def build_snapshot(
        self, user_id: str, query: BuildPortfolioSnapshotQuery
    ) -> PortfolioSnapshot:
        with self._unit_of_work(user_id) as uow:
            transactions = self._get_converted_transaction(uow, query)
            account_map = uow.accounts.get_user_account_map()
            portfolios = self._portfolio_builder.build(
                transactions,
                account_map,
                query.reporting_currency,
                query.accounting_method,
            )
            instruments = self._get_portfolio_instruments(uow, portfolios)
            institutions, connections, accounts = self._get_portfolio_accounts(
                uow, portfolios
            )
            return PortfolioSnapshot(
                portfolios=tuple(portfolios),
                instruments=tuple(instruments),
                institutions=tuple(institutions),
                connections=tuple(connections),
                accounts=tuple(accounts),
                query=query,
            )

    def _get_converted_transaction(
        self, uow: ReadUnitOfWork, query: BuildPortfolioSnapshotQuery
    ) -> Iterator[ConvertedTransaction]:
        transactions: Iterable[Transaction] = uow.transactions.get(
            filter_=(
                FilterNode("executed_at", Operator.LE, query.as_of, Transaction)
                if query.as_of
                else None
            ),
            sorts=[self._REQUIRED_TRANSACTION_SORT],
        )
        instrument_ids = uow.transactions.get_distinct_instrument_ids()
        splits_list = uow.market_data.get_stock_splits_by_instrument_ids(instrument_ids)
        adjustied_transactions = self._transaction_adjuster.adjust(
            transactions, splits_list
        )

        transaction_dates = uow.transactions.get_distinct_dates()
        rates_by_date = uow.fx_rates.get_by_dates_required(transaction_dates)
        converter = TransactionConverter(rates_by_date)

        return converter.convert_many(adjustied_transactions, query.reporting_currency)

    def _get_portfolio_instruments(
        self,
        uow: ReadUnitOfWork,
        portfolios: list[Portfolio],
    ) -> list[Instrument]:
        return uow.instruments.get_by_ids(
            instrument_ids={
                instrument_id
                for portfolio in portfolios
                for instrument_id in portfolio.instrument_ids
            }
        )

    def _get_portfolio_accounts(
        self,
        uow: ReadUnitOfWork,
        portfolios: list[Portfolio],
    ) -> tuple[list[Institution], list[InstitutionConnection], list[AssetAccount]]:
        connection_ids: set[str] = {
            portfolio.scope.connection_id
            for portfolio in portfolios
            if portfolio.scope.connection_id
        }
        account_ids: set[str] = {
            portfolio.scope.account_id
            for portfolio in portfolios
            if portfolio.scope.account_id
        }
        accounts = uow.accounts.get_by_ids(account_ids)
        connections = uow.institution_connections.get_by_ids(connection_ids)
        institutions = [
            self._institution_registry.get_institution(connection.institution_id)
            for connection in connections
        ]
        return institutions, connections, accounts

    def _process_snapshot(
        self,
        snapshot: PortfolioSnapshot,
        query: ViewPortfolioSnapshotQuery,
        market_data: MarketData | None = None,
    ) -> list[ValuedPortfolio]:
        entity_filters = self._filter_mapper.map(query.options.filter)

        portfolios: Iterable[Portfolio] = snapshot.portfolios
        if filter_ := entity_filters.get(Portfolio):
            portfolios = list(filter_.apply(portfolios))

        portfolios = self._portfolio_builder.consolidate(portfolios, query.scope_type)

        valued_portfolios = self._value_portfolios(
            portfolios, snapshot.instruments, snapshot.query.reporting_currency, market_data
        )
        if filter_ := entity_filters.get(ValuedPortfolio):
            valued_portfolios = list(filter_.apply(valued_portfolios))

        return valued_portfolios

    def _get_portfolio_valuations(
        self,
        portfolios: Iterable[Portfolio],
        instruments: Iterable[Instrument],
        reporting_currency: Currency,
        market_data: MarketData | None = None,
    ) -> dict[str | None, PortfolioValuation]:
        instruments_metadata = {
            instrument.id: instrument.metadata for instrument in instruments
        }
        if market_data is None:
            market_data = self.fetch_market_data(instruments_metadata.values())

        if market_data is None:
            return {}

        return {
            portfolio.scope.id: self._portfolio_valuation_engine.get_valuation(
                portfolio,
                instruments_metadata,
                reporting_currency,
                market_data,
            )
            for portfolio in portfolios
        }

    def _value_portfolios(
        self,
        portfolios: Iterable[Portfolio],
        instruments: Iterable[Instrument],
        reporting_currency: Currency,
        market_data: MarketData | None = None,
    ) -> list[ValuedPortfolio]:
        valuations = self._get_portfolio_valuations(
            portfolios, instruments, reporting_currency, market_data
        )
        return [
            ValuedPortfolio(
                portfolio=portfolio,
                valuation=valuations.get(portfolio.scope.id),
            )
            for portfolio in portfolios
        ]

    def fetch_market_data(self, instruments: Iterable[Instrument | InstrumentMetadata]) -> MarketData | None:
        if cached_rates := self._fx_service.cached_spot_rates:
            rates = cached_rates

        else:
            try:
                rates = self._fx_service.get_spot_rates()
            except FxClientError:
                return None

        if cached_prices := self._market_data_service.cached_prices(instruments):
            prices = cached_prices

        else:
            try:
                prices = self._market_data_service.get_spot_prices(instruments)
            except MarketDataClientError:
                return None

        return MarketData(rates=rates, prices=prices)
