from dataclasses import dataclass

from portfolio_tracker.application.views import TransactionView
from portfolio_tracker.presentation.shared.fromatters import format_quantity

from .spec import (
    ColumnSpec,
    TableSpec,
    Tone,
    datetime_column,
    money_column,
    number_column,
    text_column,
)


@dataclass(frozen=True, kw_only=True)
class TransactionViewTableSpec(TableSpec[TransactionView]):
    name = "transaction"
    title = "Transactions"

    transaction_id: ColumnSpec = text_column("id", "ID")
    executed_at: ColumnSpec = datetime_column("executed_at", "Executed At")
    account_name: ColumnSpec = text_column("account.name", "Account")
    type: ColumnSpec = text_column("type", "Type")
    instrument_symbol: ColumnSpec = text_column("instrument.symbol", "Symbol")
    quantity: ColumnSpec = number_column(
        "quantity", "Quantity", formatter=format_quantity
    )
    price: ColumnSpec = money_column("price.native", "Price")
    fee: ColumnSpec = money_column("fee.native", "Fee")
    tax: ColumnSpec = money_column("tax.native", "Tax")
    cash_impact: ColumnSpec = money_column(
        "cash_impact.native",
        "Cash Impact",
        tone=Tone.PROFIT_OR_LOSS,
        total_field="cash_impact",
    )
