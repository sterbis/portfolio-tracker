from collections.abc import Iterable
from datetime import datetime, timezone
from types import MappingProxyType

from portfolio_tracker.application.shared.errors import MarketDataClientError
from portfolio_tracker.domain.instrument import Instrument, InstrumentMetadata
from portfolio_tracker.domain.market_data import StockSplits, MarketPrices
from portfolio_tracker.domain.shared import Money

from .client import MarketDataClient


class MarketDataService:
    def __init__(
        self,
        market_data_client: MarketDataClient,
        prices_cache_ttl: int = 10,
    ):
        self._market_data_client = market_data_client
        self._prices_cache_ttl = prices_cache_ttl
        self._cached_prices: MarketPrices | None = None

    def cached_prices(self, instruments: Iterable[Instrument | InstrumentMetadata]) -> MarketPrices | None:
        if not instruments:
            return MarketPrices(prices=MappingProxyType({}))

        if self._cached_prices is None:
            return None

        required_ids = {instrument.id for instrument in instruments}
        cached_ids = set(self._cached_prices.prices)
        if not required_ids.issubset(cached_ids):
            return None

        now = datetime.now(tz=timezone.utc)
        age = (now - self._cached_prices.as_of).total_seconds()
        if age > self._prices_cache_ttl:
            return None

        return self._cached_prices

    def get_spot_prices(
        self,
        instruments: Iterable[Instrument | InstrumentMetadata],
        extended_hours: bool = False,
    ) -> MarketPrices:
        if cached_prices := self.cached_prices(instruments):
            return cached_prices
    
        instrument_by_symbol = {instrument.symbol: instrument for instrument in instruments}
        symbols = set(instrument_by_symbol.keys())

        now = datetime.now(tz=timezone.utc)
        price_by_symbol = self._market_data_client.fetch_spot_prices(
            symbols, extended_hours
        )

        missing_symbols = symbols - price_by_symbol.keys()
        if missing_symbols:
            formatted_symbols = ", ".join(sorted(missing_symbols))
            raise MarketDataClientError(
                f"Failed to fetch spot prices for following symbols: {formatted_symbols}"
            )

        return MarketPrices(
            as_of=now,
            prices=MappingProxyType(
                {
                    instrument_by_symbol[symbol].id: Money(
                        amount=price, currency=instrument_by_symbol[symbol].currency
                    )
                    for symbol, price in price_by_symbol.items()
                    if price is not None
                }
            )
        )

    def get_stock_splits(
        self, instrument: Instrument | InstrumentMetadata, restore: bool = False
    ) -> StockSplits | None:
        start = None if restore else instrument.last_synced_at

        splits = self._market_data_client.fetch_stock_splits(
            instrument.symbol, start
        )
        return (
            StockSplits(
                instrument_id=instrument.id,
                splits=splits,
            )
            if splits
            else None
        )
