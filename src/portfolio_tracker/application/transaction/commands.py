from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from portfolio_tracker.application.views.shared import MoneyView
from portfolio_tracker.domain.transaction import TransactionType


@dataclass(frozen=True)
class TransactionPayloadDto:
    executed_at: datetime
    account_id: str
    type: TransactionType
    instrument_id: str | None
    quantity: Decimal
    price: MoneyView
    fee: MoneyView
    tax: MoneyView
    cash_impact: MoneyView
    correlation_id: str | None


@dataclass(frozen=True)
class CreateTransactionCommand:
    payload: TransactionPayloadDto


@dataclass(frozen=True)
class UpdateTransactionCommand:
    transaction_id: str
    payload: TransactionPayloadDto
