import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from portfolio_tracker.domain.shared import Money


class TransactionType(Enum):
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


@dataclass(frozen=True)
class Transaction:
    correlation_id: str | None
    executed_at: datetime
    asset_account_id: str
    type: TransactionType
    instrument_id: str | None
    quantity: Decimal
    price: Money
    fee: Money
    tax: Money
    cash_impact: Money
    _id: str | None = None

    @property
    def id(self) -> str:
        assert self._id is not None
        return self._id

    def __post_init__(self) -> None:
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

        hash_string = (
            f"{self.asset_account_id}|"
            f"{self.executed_at.isoformat()}|"
            f"{self.type.value}|"
            f"{self.instrument_id if self.instrument_id else ''}|"
            f"{self.quantity.normalize()}|"
            f"{self.price}|"
            f"{self.fee}|"
            f"{self.tax}|"
        )
        hash_digest = hashlib.sha256(hash_string.encode("utf-8")).hexdigest()[:16]
        transaction_id = f"tr_{hash_digest}"

        if self._id is None:
            object.__setattr__(self, "_id", transaction_id)

        elif self._id != transaction_id:
            raise ValueError(
                f"Provided instrument id {self._id} does not match generated id {transaction_id}."
            )
