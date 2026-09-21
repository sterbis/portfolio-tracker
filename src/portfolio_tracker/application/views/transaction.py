from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.domain.transaction import (
    ConvertedTransaction,
    Transaction,
    TransactionType,
)

from .account import AssetAccountView
from .instrument import InstrumentView
from .shared import DualMoneyView, MoneyView


@dataclass(frozen=True, kw_only=True)
class TransactionView:
    id: str
    correlation_id: str | None = None
    executed_at: datetime
    account: AssetAccountView
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
        account_view: AssetAccountView,
        instrument_view: InstrumentView | None = None,
    ) -> TransactionView:
        return cls(
            id=transaction.id,
            correlation_id=transaction.correlation_id,
            executed_at=transaction.executed_at,
            account=account_view,
            type=transaction.type,
            instrument=instrument_view,
            quantity=transaction.quantity,
            price=DualMoneyView.from_domain(transaction.price),
            fee=DualMoneyView.from_domain(transaction.fee),
            tax=DualMoneyView.from_domain(transaction.tax),
            cash_impact=DualMoneyView.from_domain(transaction.cash_impact),
        )


@dataclass(frozen=True, kw_only=True)
class TransactionTotalView:
    cash_impact: MoneyView

    @classmethod
    def from_views(
        cls, views: list[TransactionView], reporting_currency: Currency
    ) -> TransactionTotalView:
        if not views:
            return cls(
                cash_impact=MoneyView(amount=Decimal("0"), currency=reporting_currency),
            )

        return cls(
            cash_impact=MoneyView(
                amount=sum(
                    (view.cash_impact.reporting.amount for view in views),
                    start=Decimal("0"),
                ),
                currency=reporting_currency,
            )
        )


@dataclass(frozen=True, kw_only=True)
class TransactionPlainView:
    id: str
    correlation_id: str | None = None
    executed_at: datetime
    account_id: str
    type: TransactionType
    instrument_id: str | None = None
    quantity: Decimal
    price: MoneyView
    fee: MoneyView
    tax: MoneyView
    cash_impact: MoneyView

    @classmethod
    def from_domain(cls, transaction: Transaction) -> TransactionPlainView:
        return cls(
            id=transaction.id,
            correlation_id=transaction.correlation_id,
            executed_at=transaction.executed_at,
            account_id=transaction.account_id,
            type=transaction.type,
            instrument_id=transaction.instrument_id,
            quantity=transaction.quantity,
            price=MoneyView.from_domain(transaction.price),
            fee=MoneyView.from_domain(transaction.fee),
            tax=MoneyView.from_domain(transaction.tax),
            cash_impact=MoneyView.from_domain(transaction.cash_impact),
        )
