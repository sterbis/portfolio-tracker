from collections.abc import Iterable
from datetime import date

from portfolio_tracker.domain.analytics.cash_balance import CashBalanceBuilder
from portfolio_tracker.domain.analytics.position import (
    AccountingMethod,
    PositionBuilder,
)
from portfolio_tracker.domain.ledger import Transaction, TransactionType
from portfolio_tracker.domain.market_data import FxRates

from .models import ConsolidationScope, Portfolio


class PortfolioBuilder:
    def __init__(
        self,
        accounting_method: AccountingMethod = AccountingMethod.FIFO,
    ):
        self._accounting_method = accounting_method

    def build(
        self,
        transactions: Iterable[Transaction],
        rates_by_date: dict[date, FxRates],
        reporting_currency: str,
    ) -> list[Portfolio]:
        position_builders, cash_balance_builders = self._process_transactions(
            transactions, rates_by_date, reporting_currency
        )

        portfolios: list[Portfolio] = []

        for asset_account_id in position_builders.keys() | cash_balance_builders.keys():
            positions = []

            for position_builder in position_builders.get(
                asset_account_id, {}
            ).values():
                if position_builder.quantity == 0:
                    continue

                positions.append(position_builder.get_position_snapshot())

            cash_balance_builder = cash_balance_builders[asset_account_id]
            cash_balance = cash_balance_builder.get_cash_balance_snapshot()

            portfolios.append(
                Portfolio(
                    scope=ConsolidationScope.ASSET_ACCOUNT,
                    account_id=asset_account_id,
                    reporting_currency=reporting_currency,
                    positions=positions,
                    cash_balance=cash_balance,
                )
            )

        return portfolios

    def _process_transactions(
        self,
        transactions: Iterable[Transaction],
        rates_by_date: dict[date, FxRates],
        reporting_currency: str,
    ) -> tuple[dict[str, dict[str, PositionBuilder]], dict[str, CashBalanceBuilder]]:
        position_builders: dict[str, dict[str, PositionBuilder]] = {}
        cash_balance_builder: dict[str, CashBalanceBuilder] = {}

        for transaction in transactions:
            asset_account_id = transaction.asset_account_id

            if asset_account_id not in cash_balance_builder:
                cash_balance_builder[asset_account_id] = CashBalanceBuilder()

            cash_balance_builder[asset_account_id].add(transaction)

            if transaction.type not in (TransactionType.BUY, TransactionType.SELL):
                continue

            assert transaction.instrument_id is not None
            instrument_id = transaction.instrument_id

            if asset_account_id not in position_builders:
                position_builders[asset_account_id] = {}

            if instrument_id not in position_builders[asset_account_id]:
                position_builders[asset_account_id][instrument_id] = PositionBuilder(
                    instrument_id=transaction.instrument_id,
                    native_currency=transaction.price.currency,
                    reporting_currency=reporting_currency,
                    accounting_method=self._accounting_method,
                )

            rates = rates_by_date[transaction.executed_at.date()]

            position_builders[asset_account_id][instrument_id].add(transaction, rates)

        return position_builders, cash_balance_builder

    def consolidate(
        self,
        portfolios: list[Portfolio],
        scope: ConsolidationScope,
        account_id_map: dict[str, str],
    ) -> list[Portfolio]:
        if scope == ConsolidationScope.ASSET_ACCOUNT:
            return portfolios

        if scope == ConsolidationScope.INSTITUTION_ACCOUNT:
            consolidated_portfolios: dict[str, Portfolio] = {}
            for portfolio in portfolios:
                assert portfolio.account_id is not None
                institution_account_id = account_id_map[portfolio.account_id]

                if institution_account_id not in consolidated_portfolios:
                    consolidated_portfolios[institution_account_id] = Portfolio(
                        scope=ConsolidationScope.INSTITUTION_ACCOUNT,
                        account_id=institution_account_id,
                        reporting_currency=portfolio.reporting_currency,
                        positions=portfolio.positions,
                        cash_balance=portfolio.cash_balance,
                    )
                else:
                    consolidated_portfolios[institution_account_id] += portfolio

            return list(consolidated_portfolios.values())

        if scope == ConsolidationScope.GLOBAL:
            consolidated_portfolio = portfolios[0]
            for portfolio in portfolios[1:]:
                consolidated_portfolio += portfolio

            return [consolidated_portfolio]

        raise ValueError(f"Unexpected consolidation scope: {scope}.")
