from collections.abc import Iterable

from portfolio_tracker.domain.account import AccountMap
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.domain.transaction import ConvertedTransaction, TransactionType

from .cash_balance import CashBalanceBuilder
from .models import Portfolio, Scope, ScopeType
from .position import AccountingMethod, PositionBuilder


class PortfolioBuilder:
    def build(
        self,
        transactions: Iterable[ConvertedTransaction],
        account_map: AccountMap,
        reporting_currency: Currency,
        accounting_method: AccountingMethod,
    ) -> list[Portfolio]:
        position_builders, cash_balance_builders = self._process_transactions(
            transactions, accounting_method
        )

        portfolios: list[Portfolio] = []

        for account_id in position_builders.keys() | cash_balance_builders.keys():
            positions = []

            for position_builder in position_builders.get(account_id, {}).values():
                if position_builder.quantity == 0:
                    continue

                positions.append(position_builder.get_position_snapshot())

            cash_balance_builder = cash_balance_builders[account_id]
            cash_balance = cash_balance_builder.get_cash_balance_snapshot()

            portfolios.append(
                Portfolio(
                    scope=Scope(
                        type=ScopeType.ACCOUNT,
                        connection_id=account_map.account_id_to_connection_id[
                            account_id
                        ],
                        account_id=account_id,
                    ),
                    reporting_currency=reporting_currency,
                    positions=positions,
                    cash_balance=cash_balance,
                )
            )

        return portfolios

    def _process_transactions(
        self,
        transactions: Iterable[ConvertedTransaction],
        accounting_method: AccountingMethod,
    ) -> tuple[dict[str, dict[str, PositionBuilder]], dict[str, CashBalanceBuilder]]:
        position_builders: dict[str, dict[str, PositionBuilder]] = {}
        cash_balance_builder: dict[str, CashBalanceBuilder] = {}

        for transaction in transactions:
            account_id = transaction.account_id

            if account_id not in cash_balance_builder:
                cash_balance_builder[account_id] = CashBalanceBuilder()

            cash_balance_builder[account_id].add(transaction)

            if transaction.type not in (TransactionType.BUY, TransactionType.SELL):
                continue

            assert transaction.instrument_id is not None
            instrument_id = transaction.instrument_id

            if account_id not in position_builders:
                position_builders[account_id] = {}

            if instrument_id not in position_builders[account_id]:
                position_builders[account_id][instrument_id] = PositionBuilder(
                    instrument_id=instrument_id,
                    native_currency=transaction.price.native.currency,
                    reporting_currency=transaction.price.reporting.currency,
                    accounting_method=accounting_method,
                )

            position_builders[account_id][instrument_id].add(transaction)

        return position_builders, cash_balance_builder

    def consolidate(
        self,
        portfolios: Iterable[Portfolio],
        scope_type: ScopeType,
    ) -> list[Portfolio]:
        if not portfolios:
            return []

        portfolios = list(portfolios)
        if scope_type == ScopeType.ACCOUNT:
            return portfolios

        if scope_type == ScopeType.INSTITUTION:
            consolidated_portfolios: dict[str, Portfolio] = {}
            for portfolio in portfolios:
                connection_id = portfolio.scope.connection_id
                assert connection_id is not None

                if connection_id not in consolidated_portfolios:
                    consolidated_portfolios[connection_id] = Portfolio(
                        scope=Scope(
                            type=ScopeType.INSTITUTION,
                            connection_id=connection_id,
                            account_id=None,
                        ),
                        reporting_currency=portfolio.reporting_currency,
                        positions=portfolio.positions,
                        cash_balance=portfolio.cash_balance,
                    )

                else:
                    consolidated_portfolios[connection_id] += portfolio

            return list(consolidated_portfolios.values())

        if scope_type == ScopeType.GLOBAL:
            consolidated_portfolio = portfolios[0]
            for portfolio in portfolios[1:]:
                consolidated_portfolio += portfolio

            return [consolidated_portfolio]

        raise ValueError(f"Unexpected consolidation scope type: {scope_type}.")
