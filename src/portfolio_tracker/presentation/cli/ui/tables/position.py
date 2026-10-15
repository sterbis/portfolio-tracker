from dataclasses import dataclass

from portfolio_tracker.application.views import PositionRowView
from portfolio_tracker.presentation.cli.ui.fromatters import format_quantity

from .scope import ScopeViewTableSpec
from .spec import (
    ColumnSpec,
    datetime_column,
    money_column,
    number_column,
    percent_column,
    text_column,
)


@dataclass(frozen=True, kw_only=True)
class PositionRowViewTableSpec(ScopeViewTableSpec[PositionRowView]):
    name = "position"
    title = "Positions"

    instrument_type: ColumnSpec = text_column("position.instrument.type", "Type")
    instrument_asset_class: ColumnSpec = text_column(
        "position.instrument.asset_class", "Asset Class"
    )
    instrument_name: ColumnSpec = text_column("position.instrument.name", "Name")
    instrument_exchange: ColumnSpec = text_column(
        "position.instrument.exchange", "Exchange"
    )
    instrument_symbol: ColumnSpec = text_column("position.instrument.symbol", "Symbol")
    quantity: ColumnSpec = number_column(
        "position.quantity", "Quantity", formatter=format_quantity
    )
    cost_basis: ColumnSpec = money_column(
        "position.cost_basis.reporting", "Cost Basis", total_field="cost_basis"
    )
    average_price: ColumnSpec = money_column(
        "position.average_price.reporting", "Average Price"
    )
    fees: ColumnSpec = money_column("position.fees.reporting", "Fees")
    opened_at: ColumnSpec = datetime_column("position.opened_at", "Opened At")
    last_trade_at: ColumnSpec = datetime_column(
        "position.last_trade_at", "Last Trade At"
    )
    last_trade_type: ColumnSpec = text_column(
        "position.last_trade_type", "Last Trade Type"
    )
    market_price: ColumnSpec = money_column("valuation.market_price.reporting", "Price")
    market_value: ColumnSpec = money_column(
        "valuation.market_value.reporting", "Market Value", total_field="market_value"
    )
    portfolio_weight: ColumnSpec = percent_column(
        "valuation.portfolio_weight", "% of Portfolio"
    )
    invested_capital_weight: ColumnSpec = percent_column(
        "valuation.invested_capital_weight",
        "% of Investments",
        total_field="invested_capital_weight",
    )
    unrealized_pnl: ColumnSpec = money_column(
        "valuation.unrealized_pnl.reporting",
        "Unrealized PnL",
        profit_and_loss=True,
        total_field="unrealized_pnl",
    )
    unrealized_pnl_percent: ColumnSpec = percent_column(
        "valuation.reporting_unrealized_pnl_percent",
        "Unrealized PnL %",
        profit_and_loss=True,
        total_field="unrealized_pnl_percent",
    )
