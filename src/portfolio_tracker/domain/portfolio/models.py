from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from functools import total_ordering
from typing import Any

from portfolio_tracker.domain.instrument import AssetClass, InstrumentType
from portfolio_tracker.domain.shared import Currency, Money

from .cash_balance import CashBalance, CashBalanceValuation
from .position import Position, PositionValuation


@total_ordering
class ScopeType(StrEnum):
    ACCOUNT = "ACCOUNT"
    INSTITUTION = "INSTITUTION"
    GLOBAL = "GLOBAL"

    @property
    def level(self) -> int:
        try:
            return _SCOPE_LEVELS[self]
        except KeyError as error:
            raise ValueError(f"Unexpected scope type: '{self}'.") from error

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ScopeType):
            return False

        return self is other

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, ScopeType):
            raise TypeError(
                f"'<' not supported between instances of 'ScopeType' and '{type(other).__name__}'"
            )

        return self.level < other.level

    def __hash__(self) -> int:
        return super().__hash__()


_SCOPE_LEVELS = {
    ScopeType.ACCOUNT: 0,
    ScopeType.INSTITUTION: 1,
    ScopeType.GLOBAL: 2,
}


@dataclass(frozen=True)
class Scope:
    type: ScopeType
    id: str | None


@dataclass(frozen=True)
class Portfolio:
    scope: Scope
    reporting_currency: Currency
    positions: list[Position]
    cash_balance: CashBalance

    @property
    def instrument_ids(self) -> set[str]:
        return {position.instrument_id for position in self.positions}

    def __add__(self, other: Portfolio) -> Portfolio:
        if not isinstance(other, Portfolio):
            return NotImplemented

        if self.scope.id == other.scope.id:
            raise ValueError(
                f"Cannot consolidate portfolio with itself. Portfolio scope id: {self.scope.id}."
            )

        if self.reporting_currency != other.reporting_currency:
            raise ValueError(
                "Currecy mismatch. Cannot consolidate portfolios with different reporting currencies. "
                f"Expected: {self.reporting_currency}, got: {other.reporting_currency}."
            )

        if self.scope.type < other.scope.type:
            return other + self

        if self.scope.type > other.scope.type:
            scope = self.scope

        elif self.scope.type == ScopeType.GLOBAL:
            raise ValueError("Cannot consolidate multiple global portfolios.")

        else:
            scope = Scope(type=ScopeType.GLOBAL, id=None)

        combined_cash_balance = self.cash_balance + other.cash_balance
        combined_positions: dict[str, Position] = {}

        for position in self.positions + other.positions:
            instrument_id = position.instrument_id
            if instrument_id not in combined_positions:
                combined_positions[instrument_id] = position
            else:
                combined_positions[instrument_id] += position

        return Portfolio(
            scope=scope,
            reporting_currency=self.reporting_currency,
            positions=list(combined_positions.values()),
            cash_balance=combined_cash_balance,
        )


@dataclass(frozen=True)
class PortfolioValuation:
    positions: dict[str, PositionValuation]
    cash_balance: CashBalanceValuation

    market_value: Money
    unrealized_pnl: Money
    asset_allocation: dict[AssetClass, tuple[Money, Decimal | None]]
    instrument_type_allocation: dict[InstrumentType, tuple[Money, Decimal | None]]

    is_partially_valued: bool = True


@dataclass(frozen=True)
class ValuedPortfolio:
    portfolio: Portfolio
    valuation: PortfolioValuation | None
