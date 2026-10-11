from collections import defaultdict
from decimal import Decimal

from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.instrument import (
    AssetClass,
    InstrumentMetadata,
    InstrumentType,
)
from portfolio_tracker.domain.portfolio.cash_balance import (
    CashBalanceValuationEngine,
)
from portfolio_tracker.domain.portfolio.position import (
    PositionValuation,
    PositionValuationEngine,
)
from portfolio_tracker.domain.shared import DualMoney, Money

from .models import Portfolio, PortfolioValuation, ValuedPortfolio


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
        instruments_metadata: list[InstrumentMetadata],
        native_market_prices: dict[str, Money | None],
        rates: FxRates,
    ) -> PortfolioValuation:
        instrument_metadata_by_id = {
            instrument_metadata.id: instrument_metadata
            for instrument_metadata in instruments_metadata
        }
        is_partially_valued = False
        reporting_currency = portfolio.reporting_currency

        reporting_market_prices: dict[str, Money] = {}
        total_position_value = Money.zero(reporting_currency)
        market_value_by_asset_class: dict[AssetClass, Money] = defaultdict(
            lambda: Money.zero(reporting_currency)
        )
        market_value_by_instrument_type: dict[InstrumentType, Money] = defaultdict(
            lambda: Money.zero(reporting_currency)
        )

        for position in portfolio.positions:
            native_market_price = native_market_prices.get(position.instrument_id)
            reporting_market_price = (
                native_market_price.convert(reporting_currency, rates)
                if native_market_price
                else Money.zero(reporting_currency)
            )
            reporting_market_prices[position.instrument_id] = reporting_market_price

            market_value = reporting_market_price * position.quantity
            total_position_value += market_value

            instrument_metadata = instrument_metadata_by_id[position.instrument_id]
            market_value_by_asset_class[instrument_metadata.asset_class] += market_value
            market_value_by_instrument_type[instrument_metadata.type] += market_value

        cash_balance_valuation = self._cash_balance_valuation_engine.get_valuation(
            portfolio.cash_balance, reporting_currency, rates
        )
        market_value_by_asset_class[AssetClass.CASH] = (
            cash_balance_valuation.total_balance
        )
        portfolio_value = total_position_value + cash_balance_valuation.total_balance

        position_valuations: dict[str, PositionValuation] = {}
        total_position_unrealized_pnl = Money.zero(reporting_currency)

        for position in portfolio.positions:
            native_market_price = native_market_prices.get(position.instrument_id)

            if native_market_price is None:
                is_partially_valued = True
                continue

            market_price = DualMoney(
                native=native_market_price,
                reporting=reporting_market_prices[position.instrument_id],
            )
            position_valuation = self._position_valuation_engine.get_valuation(
                position, market_price, portfolio_value, total_position_value
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

    def value(
        self,
        portfolio: Portfolio,
        instruments_metadata: list[InstrumentMetadata],
        native_market_prices: dict[str, Money | None],
        rates: FxRates,
    ) -> ValuedPortfolio:
        return ValuedPortfolio(
            portfolio=portfolio,
            valuation=self.get_valuation(
                portfolio, instruments_metadata, native_market_prices, rates
            ),
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
