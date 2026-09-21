from dataclasses import dataclass
from decimal import Decimal
from enum import IntEnum

from portfolio_tracker.domain.instrument import AssetClass, InstrumentType
from portfolio_tracker.domain.shared import Currency, Money

from .cash_balance import CashBalance, CashBalanceValuation
from .position import Position, PositionValuation


class ScopeType(IntEnum):
    ACCOUNT = 1
    INSTITUTION = 2
    GLOBAL = 3


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

        if self.reporting_currency != other.reporting_currency:
            raise ValueError(
                "Currecy mismatch. Cannot consolidate portfolios with different reporting currencies. "
                f"Expected: {self.reporting_currency}, got: {other.reporting_currency}."
            )

        if self.scope.type < other.scope.type:
            return other + self

        if self.scope.type > other.scope.type:
            scope = self.scope

        else:
            if self.scope.type == ScopeType.GLOBAL:
                raise ValueError("Cannot consolidate multiple global portfolios.")

            if self.scope.id == other.scope.id:
                raise ValueError(
                    f"Cannot consolidate portfolio with itself. Portfolio scope id: {self.scope.id}."
                )

            scope = Scope(
                type=ScopeType.GLOBAL,
                id=None,
            )

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
