from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from portfolio_tracker.domain.shared import DualMoney


@dataclass(frozen=True)
class Position:
    instrument_id: str

    quantity: Decimal
    cost_basis: DualMoney
    fees: DualMoney

    opened_at: datetime
    last_trade_at: datetime
    last_trade_type: str
    last_buy_at: datetime | None = None
    closed_at: datetime | None = None

    is_tax_free: bool = False
    _tax_free_position: Position | None = None

    @property
    def native_currency(self) -> str:
        return self.cost_basis.native.currency

    @property
    def reporting_currency(self) -> str:
        return self.cost_basis.reporting.currency

    @property
    def average_price(self) -> DualMoney:
        if self.quantity == 0:
            return DualMoney.zero(self.native_currency, self.reporting_currency)
        return self.cost_basis / self.quantity

    @property
    def is_closed(self) -> bool:
        return self.quantity == 0

    @property
    def tax_free_position(self) -> Position | None:
        return self if self.is_tax_free else self._tax_free_position

    def __add__(self, other: Position) -> Position:
        if not isinstance(other, Position):
            return NotImplemented

        if self.instrument_id != other.instrument_id:
            raise ValueError(
                "Cannot add different instrument postions. "
                f"Expected '{self.instrument_id}', got '{other.instrument_id}'."
            )

        quantity = self.quantity + other.quantity

        if self.last_trade_at > other.last_trade_at:
            last_trade_at = self.last_trade_at
            last_trade_type = self.last_trade_type
        else:
            last_trade_at = other.last_trade_at
            last_trade_type = other.last_trade_type

        if self.last_buy_at and other.last_buy_at:
            last_buy_at: datetime | None = max(self.last_buy_at, other.last_buy_at)
        else:
            last_buy_at = self.last_buy_at or other.last_buy_at

        if quantity == 0:
            if self.closed_at and other.closed_at:
                closed_at: datetime | None = max(self.closed_at, other.closed_at)
            else:
                closed_at = self.closed_at or other.closed_at
        else:
            closed_at = None

        if self.is_tax_free and other.is_tax_free:
            _tax_free_position = None
        elif self.tax_free_position and other.tax_free_position:
            _tax_free_position = self.tax_free_position + other.tax_free_position
        else:
            _tax_free_position = self.tax_free_position or other.tax_free_position

        return Position(
            instrument_id=self.instrument_id,
            quantity=self.quantity + other.quantity,
            cost_basis=self.cost_basis + other.cost_basis,
            fees=self.fees + other.fees,
            opened_at=min(self.opened_at, other.opened_at),
            last_trade_at=last_trade_at,
            last_trade_type=last_trade_type,
            last_buy_at=last_buy_at,
            closed_at=closed_at,
            is_tax_free=self.is_tax_free and other.is_tax_free,
            _tax_free_position=_tax_free_position,
        )


@dataclass(frozen=True)
class PositionValuation:
    instrument_id: str

    market_price: DualMoney
    market_value: DualMoney
    unrealized_pnl: DualMoney
    native_unrealized_pnl_percent: Decimal | None
    reporting_unrealized_pnl_percent: Decimal | None

    is_tax_free: bool
    _tax_free_valuation: PositionValuation | None

    @property
    def tax_free_valuation(self) -> PositionValuation | None:
        return self if self.is_tax_free else self._tax_free_valuation


@dataclass(frozen=True)
class ValuedPosition:
    position: Position
    valuation: PositionValuation | None


@dataclass(frozen=True)
class TaxLot:
    transaction_id: str
    executed_at: datetime

    original_quantity: Decimal
    remaining_quantity: Decimal

    price: DualMoney
    fee: DualMoney

    @property
    def cost_basis(self) -> DualMoney:
        return (self.remaining_quantity * self.price) + self.fee
