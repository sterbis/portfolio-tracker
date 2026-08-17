from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from portfolio_tracker.domain.instrument import AssetClass, InstrumentType
from portfolio_tracker.domain.portfolio import (
    ConsolidationScope,
    Portfolio,
    PortfolioValuation,
)
from portfolio_tracker.domain.portfolio.cash_balance import (
    CashBalance,
    CashBalanceValuation,
)
from portfolio_tracker.domain.portfolio.position import Position, PositionValuation

from .account import AssetAccountView, InstitutionAccountView
from .instrument import InstrumentView
from .shared import DualMoneyView, MoneyView


@dataclass(frozen=True)
class PositionView:
    instrument: InstrumentView

    quantity: Decimal
    cost_basis: DualMoneyView
    average_price: DualMoneyView
    fees: DualMoneyView

    opened_at: datetime
    last_trade_at: datetime
    last_trade_type: str
    last_buy_at: datetime | None
    closed_at: datetime | None

    is_closed: bool
    is_tax_free: bool

    tax_free_position: PositionView | None

    @classmethod
    def from_domain(
        cls,
        position: Position,
        instrument_view: InstrumentView,
    ) -> PositionView:
        return cls(
            instrument=instrument_view,
            quantity=position.quantity,
            cost_basis=DualMoneyView.from_domain(position.cost_basis),
            average_price=DualMoneyView.from_domain(position.average_price),
            fees=DualMoneyView.from_domain(position.fees),
            opened_at=position.opened_at,
            last_trade_at=position.last_trade_at,
            last_trade_type=position.last_trade_type,
            last_buy_at=position.last_buy_at,
            closed_at=position.closed_at,
            is_closed=position.is_closed,
            is_tax_free=position.is_tax_free,
            tax_free_position=(
                PositionView.from_domain(position.tax_free_position, instrument_view)
                if position.tax_free_position
                else None
            ),
        )


@dataclass(frozen=True)
class PositionValuationView:
    market_price: DualMoneyView
    market_value: DualMoneyView
    unrealized_pnl: DualMoneyView
    native_unrealized_pnl_percent: Decimal | None
    reporting_unrealized_pnl_percent: Decimal | None

    tax_free_valuation: PositionValuationView | None

    @classmethod
    def from_domain(
        cls,
        valuation: PositionValuation,
    ) -> PositionValuationView:
        return cls(
            market_price=DualMoneyView.from_domain(valuation.market_price),
            market_value=DualMoneyView.from_domain(valuation.market_value),
            unrealized_pnl=DualMoneyView.from_domain(valuation.unrealized_pnl),
            native_unrealized_pnl_percent=valuation.native_unrealized_pnl_percent,
            reporting_unrealized_pnl_percent=valuation.reporting_unrealized_pnl_percent,
            tax_free_valuation=(
                PositionValuationView.from_domain(valuation.tax_free_valuation)
                if valuation.tax_free_valuation
                else None
            ),
        )


@dataclass(frozen=True)
class ValuedPositionView:
    position: PositionView
    valuation: PositionValuationView | None


@dataclass(frozen=True)
class CashBalanceView:
    currencies: dict[str, MoneyView]

    @classmethod
    def from_domain(cls, cash_balance: CashBalance) -> CashBalanceView:
        return cls(
            currencies={
                currency: MoneyView.from_domain(balance)
                for currency, balance in cash_balance.currencies.items()
            }
        )


@dataclass(frozen=True)
class CashBalanceValuationView:
    total_balance: MoneyView

    @classmethod
    def from_domain(cls, valuation: CashBalanceValuation) -> CashBalanceValuationView:
        return cls(
            total_balance=MoneyView.from_domain(valuation.total_balance),
        )


@dataclass(frozen=True)
class ValuedCashBalanceView:
    cash_balance: CashBalanceView
    valuation: CashBalanceValuationView


@dataclass(frozen=True)
class PortfolioView:
    scope: ConsolidationScope
    account: AssetAccountView | InstitutionAccountView | None
    reporting_currency: str
    positions: list[PositionView]
    cash_balance: CashBalanceView

    @classmethod
    def from_domain(
        cls,
        portfolio: Portfolio,
        account_view: AssetAccountView | InstitutionAccountView | None,
        instrument_view: dict[str, InstrumentView],
    ) -> PortfolioView:
        return cls(
            scope=portfolio.scope,
            account=account_view,
            reporting_currency=portfolio.reporting_currency,
            positions=[
                PositionView.from_domain(
                    position, instrument_view[position.instrument_id]
                )
                for position in portfolio.positions
            ],
            cash_balance=CashBalanceView.from_domain(portfolio.cash_balance),
        )


@dataclass(frozen=True)
class PortfolioValuationView:
    account_id: str | None

    positions: dict[str, PositionValuationView]
    cash_balance: CashBalanceValuationView

    market_value: MoneyView
    unrealized_pnl: MoneyView
    asset_allocation: dict[AssetClass, tuple[MoneyView, Decimal | None]]
    instrument_type_allocation: dict[InstrumentType, tuple[MoneyView, Decimal | None]]

    is_partially_valued: bool = True

    @classmethod
    def from_domain(cls, valuation: PortfolioValuation) -> PortfolioValuationView:
        return cls(
            account_id=valuation.account_id,
            positions={
                instrument_id: PositionValuationView.from_domain(position_valuation)
                for instrument_id, position_valuation in valuation.positions.items()
            },
            cash_balance=CashBalanceValuationView.from_domain(valuation.cash_balance),
            market_value=MoneyView.from_domain(valuation.market_value),
            unrealized_pnl=MoneyView.from_domain(valuation.unrealized_pnl),
            asset_allocation={
                asset_class: (MoneyView.from_domain(market_value), weight)
                for asset_class, (
                    market_value,
                    weight,
                ) in valuation.asset_allocation.items()
            },
            instrument_type_allocation={
                instrument_type: (MoneyView.from_domain(market_value), weight)
                for instrument_type, (
                    market_value,
                    weight,
                ) in valuation.instrument_type_allocation.items()
            },
            is_partially_valued=valuation.is_partially_valued,
        )


@dataclass(frozen=True)
class ValuedPortfolioView:
    portfolio: PortfolioView
    valuation: PortfolioValuationView | None
