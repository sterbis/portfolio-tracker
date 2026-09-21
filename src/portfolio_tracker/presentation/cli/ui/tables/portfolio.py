from typing import Generic

from portfolio_tracker.application.views import (
    CashBalanceRowView,
    PositionRowView,
)
from portfolio_tracker.presentation.cli.ui.fromatters import format_quantity

from .view_table import (
    TView,
    ViewTable,
    datetime_column,
    money_column,
    number_column,
    text_column,
)


class ScopeViewTable(ViewTable[TView]):
    institution_name = text_column("scope.institution_name", "Institution")
    institution_account_name = text_column(
        "scope.institution_connection_name", "Institution Account"
    )
    account_name = text_column("scope.account_name", "Account")


class CashBalanceRowViewTable(ScopeViewTable[CashBalanceRowView], Generic[TView]):
    name = "cash_balance"
    title = "Cash Balance"

    currency = text_column("balance.currency", "Currency")
    amount = number_column("balance.amount", "Amount", thousand_separator=True)


class PositionRowViewTable(ScopeViewTable[PositionRowView]):
    name = "position"
    title = "Positions"

    instrument_type = text_column("position.instrument.type", "Type")
    instrument_asset_class = text_column(
        "position.instrument.asset_class", "Asset Class"
    )
    instrument_name = text_column("position.instrument.name", "Name")
    instrument_exchange = text_column("position.instrument.exchange", "Exchange")
    instrument_symbol = text_column("position.instrument.symbol", "Symbol")
    quantity = number_column("position.quantity", "Quantity", formatter=format_quantity)
    cost_basis = money_column("position.cost_basis.native", "Cost Basis")
    average_price = money_column("position.average_price.native", "Average Price")
    fees = money_column("position.fees.native", "Fees")
    opened_at = datetime_column("position.opened_at", "Opened At")
    last_trade_at = datetime_column("position.last_trade_at", "Last Trade At")
    last_trade_type = text_column("position.last_trade_type", "Last Trade Type")
    market_price = money_column("valuation.market_price.native", "Price")
    market_value = money_column("valuation.market_value.native", "Market Value")
    unrealized_pnl = money_column("valuation.unrealized_pnl.native", "Unrealized PnL")
    unrealized_pnl_percent = money_column(
        "valuation.native_unrealized_pnl_percent", "Unrealized PnL %"
    )
