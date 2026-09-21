import hashlib
import secrets
from dataclasses import InitVar, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum

from portfolio_tracker.domain.shared import DualMoney, Money


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
    id: str = field(default_factory=lambda: f"txn_{secrets.token_urlsafe(8)}")
    correlation_id: str | None = None
    checksum: str = field(init=False)
    provided_checksum: InitVar[str | None] = None
    account_id: str
    executed_at: datetime
    type: TransactionType
    instrument_id: str | None = None
    quantity: Decimal
    price: Money
    fee: Money
    tax: Money
    cash_impact: Money

    def __post_init__(self, provided_checksum: str | None) -> None:
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

        checksum_string = (
            f"{self.account_id}|"
            f"{self.executed_at.isoformat()}|"
            f"{self.type.value}|"
            f"{self.instrument_id if self.instrument_id else ''}|"
            f"{self.quantity.normalize()}|"
            f"{self.price}|"
            f"{self.fee}|"
            f"{self.tax}|"
        )
        checksum = hashlib.sha256(checksum_string.encode("utf-8")).hexdigest()[:16]

        if provided_checksum and provided_checksum != checksum:
            raise ValueError(
                f"Provided transaction checksum '{provided_checksum}' does not match computed checksum '{checksum}'."
            )

        object.__setattr__(self, "checksum", checksum)


@dataclass(frozen=True, kw_only=True, slots=True)
class ConvertedTransaction:
    id: str
    correlation_id: str | None
    checksum: str
    account_id: str
    executed_at: datetime
    type: TransactionType
    instrument_id: str | None
    quantity: Decimal
    price: DualMoney
    fee: DualMoney
    tax: DualMoney
    cash_impact: DualMoney
