from decimal import Decimal

from portfolio_tracker.domain.shared import DualMoney, Money

from .models import Position, PositionValuation, ValuedPosition


class PositionValuationEngine:
    def get_valuation(
        self,
        position: Position,
        market_price: DualMoney,
        portfolio_value: Money,
        total_position_value: Money,
    ) -> PositionValuation:
        market_value = market_price * position.quantity
        portfolio_weight = (
            market_value.reporting.amount / portfolio_value.amount
            if portfolio_value.amount != 0
            else Decimal("0")
        )
        invested_capital_weight = (
            market_value.reporting.amount / total_position_value.amount
            if total_position_value.amount != 0
            else Decimal("0")
        )

        unrealized_pnl = market_value - position.cost_basis
        native_unrealized_pnl_percent = reporting_unrealized_pnl_percent = None
        if (
            not position.cost_basis.native.is_zero()
            and not position.cost_basis.reporting.is_zero()
        ):
            native_unrealized_pnl_percent = (
                unrealized_pnl.native.amount / position.cost_basis.native.amount
            )
            reporting_unrealized_pnl_percent = (
                unrealized_pnl.reporting.amount / position.cost_basis.reporting.amount
            )

        tax_free_valuation = None
        if not position.is_tax_free and position.tax_free_position:
            tax_free_valuation = self.get_valuation(
                position.tax_free_position,
                market_price,
                portfolio_value,
                total_position_value,
            )

        return PositionValuation(
            instrument_id=position.instrument_id,
            market_price=market_price,
            market_value=market_value,
            portfolio_weight=portfolio_weight,
            invested_capital_weight=invested_capital_weight,
            unrealized_pnl=unrealized_pnl,
            native_unrealized_pnl_percent=native_unrealized_pnl_percent,
            reporting_unrealized_pnl_percent=reporting_unrealized_pnl_percent,
            is_tax_free=position.is_tax_free,
            _tax_free_valuation=tax_free_valuation,
        )

    def value(
        self,
        position: Position,
        market_price: DualMoney,
        portfolio_market_value: Money,
        total_position_value: Money,
    ) -> ValuedPosition:
        return ValuedPosition(
            position=position,
            valuation=self.get_valuation(
                position, market_price, portfolio_market_value, total_position_value
            ),
        )
