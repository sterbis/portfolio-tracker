from dataclasses import dataclass
from decimal import Decimal
from enum import IntEnum

from portfolio_tracker.domain.instrument import AssetClass, InstrumentType
from portfolio_tracker.domain.shared import Money

from .cash_balance import CashBalance, CashBalanceValuation
from .position import Position, PositionValuation


class ConsolidationScope(IntEnum):
    ASSET_ACCOUNT = 1
    INSTITUTION_ACCOUNT = 2
    GLOBAL = 3


@dataclass(frozen=True)
class Portfolio:
    scope: ConsolidationScope
    account_id: str | None
    reporting_currency: str
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

        if self.scope < other.scope:
            return other + self

        if self.scope > other.scope:
            scope = self.scope
            account_id = self.account_id

        else:
            if self.scope == ConsolidationScope.GLOBAL:
                raise ValueError("Cannot consolidate multiple global portfolios.")

            if self.account_id == other.account_id:
                raise ValueError(
                    f"Cannot consolidate portfolio with itself. Portfolio account id: {self.account_id}."
                )

            scope = ConsolidationScope.GLOBAL
            account_id = None

        combined_positions: dict[str, Position] = {}
        for position in self.positions + other.positions:
            instrument_id = position.instrument_id
            if instrument_id not in combined_positions:
                combined_positions[instrument_id] = position
            else:
                combined_positions[instrument_id] += position

        return Portfolio(
            scope=scope,
            account_id=account_id,
            reporting_currency=self.reporting_currency,
            positions=list(combined_positions.values()),
            cash_balance=self.cash_balance + other.cash_balance,
        )


@dataclass(frozen=True)
class PortfolioValuation:
    account_id: str | None

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
    valuation: PortfolioValuation
