from dataclasses import InitVar, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum

from portfolio_tracker.domain.shared import DualMoney, Money
from portfolio_tracker.shared.id_utils import generate_deterministic_hex_id


class TransactionType(StrEnum):
    BUY = "BUY"
    CURRENCY_EXCHANGE = "CURRENCY_EXCHANGE"
    DEPOSIT = "DEPOSIT"
    DIVIDEND = "DIVIDEND"
    FEE = "FEE"
    INTEREST = "INTEREST"
    SELL = "SELL"
    STAKING_REWARD = "STAKING_REWARD"
    TAX = "TAX"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    WITHDRAWAL = "WITHDRAWAL"


@dataclass(frozen=True, kw_only=True, slots=True)
class Transaction:
    id: str = field(init=False)
    provided_id: InitVar[str | None] = None
    correlation_id: str | None = None
    account_id: str
    executed_at: datetime
    type: TransactionType
    instrument_id: str | None = None
    quantity: Decimal
    price: Money
    fee: Money
    tax: Money
    cash_impact: Money

    def __post_init__(self, provided_id: str | None) -> None:
        if (
            self.executed_at.tzinfo is None
            or self.executed_at.utcoffset() != timezone.utc.utcoffset(None)
        ):
            raise ValueError(
                "Transaction datetime must be represented in UTC time zone."
            )
        if (
            self.type in (TransactionType.BUY, TransactionType.SELL)
            and self.instrument_id is None
        ):
            raise ValueError(
                f"Instrument not provided for {TransactionType.BUY} or {TransactionType.SELL} transaction."
            )
        if self.quantity < 0:
            raise ValueError("Transaction quantity cannot be negative.")
        if self.price.amount < 0:
            raise ValueError("Transaction price cannot be negative.")

        data = (
            f"{self.account_id}|"
            f"{self.executed_at.isoformat()}|"
            f"{self.type.value}|"
            f"{self.instrument_id if self.instrument_id else ''}|"
            f"{self.quantity.normalize()}|"
            f"{self.price}|"
            f"{self.fee}|"
            f"{self.tax}|"
            f"{self.cash_impact}|"
        )
        id_ = generate_deterministic_hex_id(prefix="txn", data=data)
        if provided_id and provided_id != id_:
            raise ValueError(
                f"Provided transaction id '{provided_id}' does not match generated id '{id_}'."
            )

        object.__setattr__(self, "id", id_)


@dataclass(frozen=True, kw_only=True, slots=True)
class ConvertedTransaction:
    id: str
    correlation_id: str | None
    account_id: str
    executed_at: datetime
    type: TransactionType
    instrument_id: str | None
    quantity: Decimal
    price: DualMoney
    fee: DualMoney
    tax: DualMoney
    cash_impact: DualMoney
