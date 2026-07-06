from collections import defaultdict
from decimal import Decimal

from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.instrument import (
    AssetClass,
    InstrumentMetadata,
    InstrumentType,
)
from portfolio_tracker.domain.portfolio.cash_balance import CashBalanceEvaluator
from portfolio_tracker.domain.portfolio.position import (
    PositionEvaluator,
    PositionValuation,
)
from portfolio_tracker.domain.shared import DualMoney, Money

from .models import Portfolio, PortfolioValuation


class PortfolioEvaluator:
    def __init__(
        self,
        cash_balance_evaluator: CashBalanceEvaluator,
        position_evaluator: PositionEvaluator,
    ) -> None:
        self._cash_balance_evaluator = cash_balance_evaluator
        self._position_evaluator = position_evaluator

    def evaluate(
        self,
        portfolio: Portfolio,
        instruments_metadata: list[InstrumentMetadata],
        native_market_prices: dict[str, Money],
        rates: FxRates,
    ) -> PortfolioValuation:
        instrument_metadata_by_id = {
            instrument_metadata.id: instrument_metadata
            for instrument_metadata in instruments_metadata
        }

        cash_balance_valuation = self._cash_balance_evaluator.evaluate(
            portfolio.cash_balance, portfolio.reporting_currency, rates
        )

        position_valuations: dict[str, PositionValuation] = {}
        is_partially_valued = False

        positions_market_value = Money.zero(portfolio.reporting_currency)
        portfolio_unrealized_pnl_amount = Money.zero(portfolio.reporting_currency)
        market_value_by_asset_class: dict[AssetClass, Money] = defaultdict(
            lambda: Money.zero(portfolio.reporting_currency)
        )
        market_value_by_instrument_type: dict[InstrumentType, Money] = defaultdict(
            lambda: Money.zero(portfolio.reporting_currency)
        )

        for position in portfolio.positions:
            instrument_id = position.instrument_id
            instrument_metadata = instrument_metadata_by_id[instrument_id]
            native_market_price = native_market_prices.get(instrument_id)

            if not native_market_price:
                is_partially_valued = True
                continue

            rate = rates.get_rate(
                position.native_currency,
                portfolio.reporting_currency,
            )
            market_price = DualMoney(native_market_price, native_market_price * rate)

            position_valuation = self._position_evaluator.evaluate(
                position, market_price
            )
            position_valuations[instrument_id] = position_valuation

            positions_market_value += position_valuation.market_value.reporting
            portfolio_unrealized_pnl_amount += (
                position_valuation.unrealized_pnl.reporting
            )

            market_value_by_asset_class[
                instrument_metadata.asset_class
            ] += position_valuation.market_value.reporting
            market_value_by_instrument_type[
                instrument_metadata.type
            ] += position_valuation.market_value.reporting

        total_balance = cash_balance_valuation.total_balance

        portfolio_market_value = positions_market_value + total_balance

        market_value_by_asset_class[AssetClass.CASH] = total_balance

        asset_allocation, instrument_type_allocation = self._get_allocations(
            portfolio_market_value,
            positions_market_value,
            market_value_by_asset_class,
            market_value_by_instrument_type,
        )

        return PortfolioValuation(
            account_id=portfolio.account_id,
            positions=position_valuations,
            cash_balance=cash_balance_valuation,
            market_value=portfolio_market_value,
            unrealized_pnl=portfolio_unrealized_pnl_amount,
            asset_allocation=asset_allocation,
            instrument_type_allocation=instrument_type_allocation,
            is_partially_valued=is_partially_valued,
        )

    def _get_allocations(
        self,
        portfolio_market_value: Money,
        positions_market_value: Money,
        market_value_by_asset_class: dict[AssetClass, Money],
        market_value_by_instrument_type: dict[InstrumentType, Money],
    ) -> tuple[
        dict[AssetClass, tuple[Money, Decimal | None]],
        dict[InstrumentType, tuple[Money, Decimal | None]],
    ]:
        asset_allocation_percent = True
        if portfolio_market_value.is_zero():
            asset_allocation_percent = False

        instrument_type_allocation_percent = True
        if positions_market_value.is_zero():
            instrument_type_allocation_percent = False

        asset_allocation = {
            asset_class: (
                market_value,
                (
                    market_value.amount / portfolio_market_value.amount
                    if asset_allocation_percent
                    else None
                ),
            )
            for asset_class, market_value in market_value_by_asset_class.items()
        }

        instrument_type_allocation = {
            instrument_type: (
                market_value,
                (
                    market_value.amount / positions_market_value.amount
                    if instrument_type_allocation_percent
                    else None
                ),
            )
            for instrument_type, market_value in market_value_by_instrument_type.items()
        }

        return asset_allocation, instrument_type_allocation
