from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field
from decimal import Decimal
from enum import StrEnum
from functools import total_ordering
from typing import TYPE_CHECKING

from portfolio_tracker.shared.id_utils import generate_deterministic_hex_id

if TYPE_CHECKING:
    from portfolio_tracker.domain.fx import FxRates


class Currency(StrEnum):
    CZK = "CZK"
    EUR = "EUR"
    USD = "USD"


@dataclass(frozen=True, kw_only=True)
class DeterministicIdEntity(ABC):
    id: str = field(init=False)
    provided_id: InitVar[str | None] = None

    @property
    @abstractmethod
    def _id_prefix(self) -> str: ...

    @property
    @abstractmethod
    def _identity(self) -> str: ...

    def __post_init__(self, provided_id: str | None) -> None:
        id_ = generate_deterministic_hex_id(self._id_prefix, self._identity)
        if provided_id is not None and provided_id != id_:
            raise ValueError(
                f"Provided {self.__class__.__name__} id '{provided_id}' does not match computed id '{id_}'."
            )

        object.__setattr__(self, "id", id_)
        self._validate()

    def _validate(self) -> None:
        pass


@total_ordering
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency

    def __str__(self) -> str:
        return f"{self.amount.normalize()} {self.currency}"

    def __bool__(self) -> bool:
        return bool(self.amount)

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented

        self._validate_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented

        self._validate_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __mul__(self, other: int | Decimal) -> Money:
        if not isinstance(other, (int, Decimal)):
            return NotImplemented

        return Money(self.amount * other, self.currency)

    def __rmul__(self, other: int | Decimal) -> Money:
        return self.__mul__(other)

    def __truediv__(self, other: int | Decimal) -> Money:
        if not isinstance(other, (int, Decimal)):
            return NotImplemented

        return Money(self.amount / Decimal(other), self.currency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented

        return self.currency == other.currency and self.amount == other.amount

    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented

        self._validate_currency(other)
        return self.amount < other.amount

    def _validate_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"Currency mismatch. Expected {self.currency}, got {other.currency}."
            )

    def is_zero(self) -> bool:
        return self.amount == Decimal("0")

    def to_zero(self) -> Money:
        return Money(amount=Decimal("0"), currency=self.currency)

    def convert(self, to_currency: Currency, rates: FxRates) -> Money:
        rate = rates.get_rate(self.currency, to_currency)
        return Money(
            amount=self.amount * rate,
            currency=to_currency,
        )

    @classmethod
    def zero(cls, currency: Currency) -> Money:
        return cls(amount=Decimal("0"), currency=currency)


@dataclass(frozen=True)
class DualMoney:
    native: Money
    reporting: Money

    def __add__(self, other: DualMoney) -> DualMoney:
        if not isinstance(other, DualMoney):
            return NotImplemented

        return DualMoney(
            native=self.native + other.native,
            reporting=self.reporting + other.reporting,
        )

    def __sub__(self, other: DualMoney) -> DualMoney:
        if not isinstance(other, DualMoney):
            return NotImplemented

        return DualMoney(
            native=self.native - other.native,
            reporting=self.reporting - other.reporting,
        )

    def __mul__(self, other: int | Decimal) -> DualMoney:
        if not isinstance(other, (int, Decimal)):
            return NotImplemented

        return DualMoney(native=self.native * other, reporting=self.reporting * other)

    def __rmul__(self, other: int | Decimal) -> DualMoney:
        return self.__mul__(other)

    def __truediv__(self, other: int | Decimal) -> DualMoney:
        return DualMoney(native=self.native / other, reporting=self.reporting / other)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DualMoney):
            return NotImplemented

        return self.native == other.native and self.reporting == other.reporting

    def is_zero(self) -> bool:
        return self.native.is_zero() and self.reporting.is_zero()

    def to_zero(self) -> DualMoney:
        return DualMoney(
            native=self.native.to_zero(),
            reporting=self.reporting.to_zero(),
        )

    @classmethod
    def zero(cls, native_currency: Currency, reporting_currency: Currency) -> DualMoney:
        return cls(
            native=Money.zero(native_currency),
            reporting=Money.zero(reporting_currency),
        )
