import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum

from portfolio_tracker.domain.shared import Money


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


@dataclass(frozen=True)
class Transaction:
    executed_at: datetime
    asset_account_id: str
    type: TransactionType
    instrument_id: str | None
    quantity: Decimal
    price: Money
    fee: Money
    tax: Money
    cash_impact: Money
    id: str = field(default_factory=lambda: f"tr_{uuid.uuid4().hex[:16]}")
    correlation_id: str | None = None
    _checksum: str | None = None

    @property
    def checksum(self) -> str:
        assert self._checksum is not None
        return self._checksum

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

        checksum_string = (
            f"{self.asset_account_id}|"
            f"{self.executed_at.isoformat()}|"
            f"{self.type.value}|"
            f"{self.instrument_id if self.instrument_id else ''}|"
            f"{self.quantity.normalize()}|"
            f"{self.price}|"
            f"{self.fee}|"
            f"{self.tax}|"
        )
        checksum = hashlib.sha256(checksum_string.encode("utf-8")).hexdigest()[:16]

        if self._checksum is None:
            object.__setattr__(self, "_checksum", checksum)

        elif self._checksum != checksum:
            raise ValueError(
                f"Provided transaction checksum '{self._checksum}' does not match computed checksum '{checksum}'."
            )
