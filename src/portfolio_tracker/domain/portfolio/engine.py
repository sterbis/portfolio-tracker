from collections import defaultdict
from decimal import Decimal

from portfolio_tracker.domain.instrument import (
    AssetClass,
    InstrumentMetadata,
    InstrumentType,
)
from portfolio_tracker.domain.market_data import MarketData
from portfolio_tracker.domain.portfolio.cash_balance import (
    CashBalanceValuationEngine,
)
from portfolio_tracker.domain.portfolio.position import (
    PositionValuation,
    PositionValuationEngine,
)
from portfolio_tracker.domain.shared import Currency, Money, DualMoney

from .models import Portfolio, PortfolioValuation


class PortfolioValuationEngine:
    def __init__(
        self,
        cash_balance_valuation_engine: CashBalanceValuationEngine,
        position_valuation_engine: PositionValuationEngine,
    ) -> None:
        self._cash_balance_valuation_engine = cash_balance_valuation_engine
        self._position_valuation_engine = position_valuation_engine

    def get_valuation(
        self,
        portfolio: Portfolio,
        instruments_metadata: dict[str, InstrumentMetadata],
        reporting_currency: Currency,
        market_data: MarketData,
    ) -> PortfolioValuation:
        is_partially_valued = False

        zero_money = Money.zero(reporting_currency)
        total_position_value = zero_money
        market_value_by_asset_class: dict[AssetClass, Money] = defaultdict(
            lambda: zero_money
        )
        market_value_by_instrument_type: dict[InstrumentType, Money] = defaultdict(
            lambda: zero_money
        )

        for position in portfolio.positions:
            native_price = market_data.prices.prices.get(position.instrument_id)
            if native_price is None:
                is_partially_valued = True
                continue

            reporting_price = native_price.convert(reporting_currency, market_data.rates)
            market_value = reporting_price * position.quantity
            total_position_value += market_value

            instrument_metadata = instruments_metadata[position.instrument_id]
            market_value_by_asset_class[instrument_metadata.asset_class] += market_value
            market_value_by_instrument_type[instrument_metadata.type] += market_value

        cash_balance_valuation = self._cash_balance_valuation_engine.get_valuation(
            portfolio.cash_balance, reporting_currency, market_data.rates
        )
        total_cash_balance = cash_balance_valuation.total_balance

        market_value_by_asset_class[AssetClass.CASH] = total_cash_balance
        portfolio_value = total_position_value + total_cash_balance

        position_valuations: dict[str, PositionValuation] = {}
        total_position_unrealized_pnl = zero_money

        for position in portfolio.positions:
            native_price = market_data.prices.prices.get(position.instrument_id)
            if native_price is None:
                continue

            reporting_price = native_price.convert(reporting_currency, market_data.rates)
            price = DualMoney(native_price, reporting_price)
            position_valuation = self._position_valuation_engine.get_valuation(
                position, price, portfolio_value, total_position_value
            )
            position_valuations[position.instrument_id] = position_valuation
            total_position_unrealized_pnl += position_valuation.unrealized_pnl.reporting

        asset_class_allocation, instrument_type_allocation = self._get_allocations(
            portfolio_value,
            total_position_value,
            market_value_by_asset_class,
            market_value_by_instrument_type,
        )

        return PortfolioValuation(
            positions=position_valuations,
            cash_balance=cash_balance_valuation,
            market_value=portfolio_value,
            unrealized_pnl=total_position_unrealized_pnl,
            asset_class_allocation=asset_class_allocation,
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
        asset_class_allocation = {
            asset_class: (
                market_value,
                (
                    None
                    if portfolio_market_value.is_zero()
                    else market_value.amount / portfolio_market_value.amount
                ),
            )
            for asset_class, market_value in market_value_by_asset_class.items()
        }

        instrument_type_allocation = {
            instrument_type: (
                market_value,
                (
                    None
                    if positions_market_value.is_zero()
                    else market_value.amount / positions_market_value.amount
                ),
            )
            for instrument_type, market_value in market_value_by_instrument_type.items()
        }

        return asset_class_allocation, instrument_type_allocation
