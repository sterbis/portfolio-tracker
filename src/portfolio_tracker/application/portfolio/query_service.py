from collections.abc import Iterable, Iterator
from dataclasses import dataclass

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
    PortfolioValuation,
    PortfolioValuationEngine,
    ValuedPortfolio,
)
from portfolio_tracker.domain.portfolio.position import AccountingMethod
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.domain.transaction import (
    ConvertedTransaction,
    Transaction,
    TransactionAdjuster,
    TransactionConverter,
)

from .queries import BuildPortfoliosQuery, GetCashBalancesQuery, GetPortfoliosQuery


@dataclass(frozen=True, kw_only=True)
class PortfoliosSnapshot:
    portfolios: tuple[Portfolio, ...]
    instruments: tuple[Instrument, ...]
    institutions: tuple[Institution, ...]
    connections: tuple[InstitutionConnection, ...]
    accounts: tuple[AssetAccount, ...]


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
            portfolio_views=self.get_portfolios(
                user_id,
                query=GetPortfoliosQuery(
                    scope=query.scope,
                    filter=query.filter,
                    build_portfolios_query=BuildPortfoliosQuery(
                        reporting_currency=query.reporting_currency,
                        as_of=query.as_of,
                        accounting_method=AccountingMethod.FIFO,
                    ),
                ),
            )
        )
        return self._apply_query_options(views, filter_=query.filter, sorts=query.sorts)

    def get_positions(
        self, user_id: str, query: GetPortfoliosQuery
    ) -> list[PositionRowView]:
        return self._apply_query_options(
            views=self._view_builder.build_position_row_views(
                portfolio_views=self.get_portfolios(user_id, query)
            ),
            filter_=query.filter,
            sorts=query.sorts,
        )

    def get_portfolios(
        self, user_id: str, query: GetPortfoliosQuery
    ) -> list[ValuedPortfolioView]:
        portfolios_snapshot = query.portfolios_snapshot
        if portfolios_snapshot is None:
            if query.build_portfolios_query is None:
                raise RuntimeError(
                    "Either PortfolioSnapshot or BuildPortfoliosQuery must be provided."
                )

            portfolios_snapshot = self.build_portfolios(
                user_id, query.build_portfolios_query
            )

        entity_filters = self._filter_mapper.map(query.filter)

        portfolios: Iterable[Portfolio] = portfolios_snapshot.portfolios
        if filter_ := entity_filters.get(Portfolio):
            portfolios = list(filter_.apply(portfolios))

        portfolios = self._portfolio_builder.consolidate(portfolios, query.scope)

        valued_portfolios = self._value_portfolios(
            portfolios, portfolios_snapshot.instruments
        )
        if filter_ := entity_filters.get(ValuedPortfolio):
            valued_portfolios = list(filter_.apply(valued_portfolios))

        return list(
            self._view_builder.build_valued_portfolio_views(
                portfolios_snapshot.institutions,
                portfolios_snapshot.connections,
                portfolios_snapshot.accounts,
                portfolios_snapshot.instruments,
                valued_portfolios,
            ).values()
        )

    def build_portfolios(
        self, user_id: str, query: BuildPortfoliosQuery
    ) -> PortfoliosSnapshot:
        with self._unit_of_work(user_id) as uow:
            transactions = self._get_converted_transaction(
                uow, query.reporting_currency
            )
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

            return PortfoliosSnapshot(
                portfolios=tuple(portfolios),
                instruments=tuple(instruments),
                institutions=tuple(institutions),
                connections=tuple(connections),
                accounts=tuple(accounts),
            )

    def _get_converted_transaction(
        self, uow: ReadUnitOfWork, reporting_currency: Currency
    ) -> Iterator[ConvertedTransaction]:
        transactions: Iterable[Transaction] = uow.transactions.get(
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

        return converter.convert_many(adjustied_transactions, reporting_currency)

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

    def _get_portfolio_valuations(
        self,
        portfolios: Iterable[Portfolio],
        instruments: Iterable[Instrument],
    ) -> dict[str | None, PortfolioValuation]:
        instruments_metadata = [instrument.metadata for instrument in instruments]
        native_market_prices = self._market_data_service.get_spot_prices(
            instruments_metadata
        )
        spot_rates = self._fx_service.get_spot_rates()
        return {
            portfolio.scope.id: self._portfolio_valuation_engine.get_valuation(
                portfolio,
                instruments_metadata,
                native_market_prices,
                spot_rates,
            )
            for portfolio in portfolios
        }

    def _value_portfolios(
        self,
        portfolios: Iterable[Portfolio],
        instruments: Iterable[Instrument],
    ) -> list[ValuedPortfolio]:
        try:
            valuations = self._get_portfolio_valuations(portfolios, instruments)
        except FxClientError, MarketDataClientError:
            valuations = {}

        return [
            ValuedPortfolio(
                portfolio=portfolio,
                valuation=valuations.get(portfolio.scope.id),
            )
            for portfolio in portfolios
        ]
