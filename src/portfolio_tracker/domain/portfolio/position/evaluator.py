from portfolio_tracker.domain.shared import DualMoney

from .models import Position, PositionValuation


class PositionEvaluator:
    def evaluate(
        self,
        position: Position,
        market_price: DualMoney,
    ) -> PositionValuation:
        market_value = market_price * position.quantity
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
            tax_free_valuation = self.evaluate(position.tax_free_position, market_price)

        return PositionValuation(
            instrument_id=position.instrument_id,
            market_price=market_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            native_unrealized_pnl_percent=native_unrealized_pnl_percent,
            reporting_unrealized_pnl_percent=reporting_unrealized_pnl_percent,
            is_tax_free=position.is_tax_free,
            _tax_free_valuation=tax_free_valuation,
        )
