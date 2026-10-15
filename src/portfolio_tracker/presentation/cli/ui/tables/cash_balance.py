from dataclasses import dataclass

from portfolio_tracker.application.views import CashBalanceRowView

from .scope import ScopeViewTableSpec
from .spec import ColumnSpec, number_column, text_column


@dataclass(frozen=True, kw_only=True)
class CashBalanceRowViewTableSpec(ScopeViewTableSpec[CashBalanceRowView]):
    name = "cash_balance"
    title = "Cash Balance"

    amount: ColumnSpec = number_column(
        "balance.amount", "Amount", thousand_separator=True
    )
    currency: ColumnSpec = text_column("balance.currency", "Currency")
