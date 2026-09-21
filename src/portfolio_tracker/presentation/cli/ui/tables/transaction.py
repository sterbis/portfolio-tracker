from portfolio_tracker.application.views import TransactionView
from portfolio_tracker.presentation.cli.ui.fromatters import format_quantity

from .view_table import (
    ViewTable,
    datetime_column,
    money_column,
    number_column,
    text_column,
)


class TransactionViewTable(ViewTable[TransactionView]):
    name = "transaction"
    title = "Transactions"

    executed_at = datetime_column("executed_at", "Executed At")
    account_name = text_column("asset_account.name", "Account")
    type = text_column("type", "Type")
    instrument_symbol = text_column("instrument.symbol", "Symbol")
    quantity = number_column("quantity", "Quantity", formatter=format_quantity)
    price = money_column("price.native", "Price")
    fee = money_column("fee.native", "Fee")
    tax = money_column("tax.native", "Tax")
    cash_impact = money_column(
        "cash_impact.reporting",
        "Cash Impact",
        total_field="cash_impact",
        profit_and_loss=True,
    )
