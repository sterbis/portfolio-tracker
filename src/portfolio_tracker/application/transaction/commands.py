from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from portfolio_tracker.domain.transaction import TransactionType

from portfolio_tracker.application.shared.dtos import MoneyDto


@dataclass(frozen=True)
class TransactionPayloadDto:
    executed_at: datetime
    asset_account_id: str
    type: TransactionType
    instrument_id: str | None
    quantity: Decimal
    price: MoneyDto
    fee: MoneyDto
    tax: MoneyDto
    cash_impact: MoneyDto
    correlation_id: str | None


@dataclass(frozen=True)
class CreateTransactionCommand:
    payload: TransactionPayloadDto


@dataclass(frozen=True)
class UpdateTransactionCommand:
    transaction_id: str
    payload: TransactionPayloadDto
