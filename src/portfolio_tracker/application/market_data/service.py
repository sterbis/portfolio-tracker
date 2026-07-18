from collections.abc import Iterable

from portfolio_tracker.domain.instrument import InstrumentMetadata
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.shared import Money

from .client import MarketDataClient
from .exceptions import MarketDataClientError, MarketDataIntegrityError


class MarketDataService:
    def __init__(
        self,
        market_data_client: MarketDataClient,
    ):
        self._market_data_client = market_data_client

    def get_spot_prices(
        self, instruments_metadata: Iterable[InstrumentMetadata]
    ) -> dict[str, Money | None]:
        instrument_metadata_by_symbol = self._get_instrument_metadata_by_symbol_map(
            instruments_metadata
        )
        symbols = set(instrument_metadata_by_symbol.keys())

        try:
            price_by_symbol = self._market_data_client.fetch_spot_prices(symbols)
        except MarketDataClientError:
            pass

        missing_symbols = symbols - price_by_symbol.keys()
        if missing_symbols:
            formatted_symbols = ", ".join(sorted(missing_symbols))
            raise MarketDataIntegrityError(
                detail=f"Missing spot price data for following symbols: {formatted_symbols}"
            )

        price_by_instrument_id: dict[str, Money | None] = {}
        for symbol, price in price_by_symbol.items():
            instrument_metadata = instrument_metadata_by_symbol[symbol]
            price_by_instrument_id[instrument_metadata.id] = (
                Money(amount=price, currency=instrument_metadata.currency)
                if price
                else None
            )

        return price_by_instrument_id

    def get_stock_splits(
        self, instruments_metadata: Iterable[InstrumentMetadata]
    ) -> list[StockSplits]:
        splits_list: list[StockSplits] = []

        for instrument_metadata in instruments_metadata:
            try:
                split_by_datetime = self._market_data_client.fetch_stock_splits(
                    instrument_metadata.symbol
                )
            except MarketDataClientError:
                continue

            if split_by_datetime:
                splits_list.append(
                    StockSplits(
                        instrument_id=instrument_metadata.id,
                        splits=split_by_datetime,
                    )
                )

        return splits_list

    def _get_instrument_metadata_by_symbol_map(
        self, instruments_metadata: Iterable[InstrumentMetadata]
    ) -> dict[str, InstrumentMetadata]:
        return {
            instrument_metadata.symbol: instrument_metadata
            for instrument_metadata in instruments_metadata
        }
