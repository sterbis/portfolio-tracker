from collections.abc import Iterable

from portfolio_tracker.application.ports.clients import (
    MarketDataClient,
    MarketDataClientError,
)
from portfolio_tracker.domain.instruments import InstrumentMetadata
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.shared import Money


class MarketDataService:
    def __init__(
        self,
        market_data_client: MarketDataClient,
    ):
        self._market_data_client = market_data_client

    def get_spot_prices(
        self, instruments_metadata: Iterable[InstrumentMetadata]
    ) -> dict[str, Money]:
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
                f"Missing spot prices for following symbols: {formatted_symbols}"
            )

        prices_by_instrument_id: dict[str, Money] = {}
        for symbol, price in price_by_symbol.items():
            instrument_metadata = instrument_metadata_by_symbol[symbol]
            prices_by_instrument_id[instrument_metadata.id] = Money(
                amount=price, currency=instrument_metadata.currency
            )

        return prices_by_instrument_id

    def fetch_stock_splits(
        self, instruments_metadata: Iterable[InstrumentMetadata]
    ) -> list[StockSplits]:
        instrument_metadata_by_symbol = self._get_instrument_metadata_by_symbol_map(
            instruments_metadata
        )

        try:
            splits_data_by_symbol = self._market_data_client.fetch_stock_splits(
                set(instrument_metadata_by_symbol.keys())
            )
        except MarketDataClientError:
            pass

        splits_list: list[StockSplits] = []
        for symbol, splits_data in splits_data_by_symbol.items():
            if instrument_metadata := instrument_metadata_by_symbol.get(symbol):
                splits_list.append(
                    StockSplits(
                        instrument_id=instrument_metadata.id,
                        splits=splits_data,
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


class MarketDataIntegrityError(Exception):
    pass
