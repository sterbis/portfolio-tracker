from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from portfolio_tracker.domain.transaction import ConvertedTransaction, TransactionType

from .account import AssetAccountView
from .instrument import InstrumentView
from .shared import DualMoneyView


@dataclass(frozen=True, kw_only=True)
class TransactionView:
    id: str
    correlation_id: str | None = None
    executed_at: datetime
    asset_account: AssetAccountView
    type: TransactionType
    instrument: InstrumentView | None = None
    quantity: Decimal
    price: DualMoneyView
    fee: DualMoneyView
    tax: DualMoneyView
    cash_impact: DualMoneyView

    @classmethod
    def from_domain(
        cls,
        transaction: ConvertedTransaction,
        asset_account_view: AssetAccountView,
        instrument_view: InstrumentView | None = None,
    ) -> TransactionView:
        return cls(
            id=transaction.id,
            correlation_id=transaction.correlation_id,
            executed_at=transaction.executed_at,
            asset_account=asset_account_view,
            type=transaction.type,
            instrument=instrument_view,
            quantity=transaction.quantity,
            price=DualMoneyView.from_domain(transaction.price),
            fee=DualMoneyView.from_domain(transaction.fee),
            tax=DualMoneyView.from_domain(transaction.tax),
            cash_impact=DualMoneyView.from_domain(transaction.cash_impact),
        )
