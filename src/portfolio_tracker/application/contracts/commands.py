from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from portfolio_tracker.application.services.accounts import Credentials
from portfolio_tracker.domain.ledger import TransactionType

from .dtos import MoneyDto


@dataclass(frozen=True)
class RegisterUserCommand:
    username: str
    password: str


@dataclass(frozen=True)
class LogInUserCommand:
    username: str
    password: str


@dataclass(frozen=True)
class ConnectInstitutionAccountCommand:
    institution_id: str
    name: str
    created_on: date
    credentials: Credentials


@dataclass(frozen=True)
class UpdateInstitutionAccountCommand:
    institution_account_id: str
    name: str
    created_on: date
    credentials: Credentials | None


@dataclass(frozen=True)
class TransactionPayload:
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
    payload: TransactionPayload


@dataclass(frozen=True)
class UpdateTransactionCommand:
    transaction_id: str
    payload: TransactionPayload


@dataclass(frozen=True)
class DeleteTransactionCommand:
    transaction_id: str
