from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import cast

import pandas as pd
import yfinance as yf

from portfolio_tracker.application.market_data import MarketDataClient


class YahooFinanceClient(MarketDataClient):
    def fetch_spot_prices(
        self, symbols: set[str], extended_hours: bool = True
    ) -> dict[str, Decimal | None]:
        prices = self._fetch_prices(
            symbols=list(symbols),
            interval="1h",
            period="1d",
            start=None,
            end=None,
            extended_hours=extended_hours,
        )

        if any(price is not None for price in prices.values()):
            return prices

        today = datetime.now(tz=timezone.utc).date()

        return self.fetch_historical_prices(symbols, today)

    def fetch_historical_prices(
        self, symbols: set[str], date_: date
    ) -> dict[str, Decimal | None]:
        return self._fetch_prices(
            symbols=list(symbols),
            interval="1d",
            period=None,
            start=date_ - timedelta(days=4),
            end=date_ + timedelta(days=1),
            extended_hours=False,
        )
    
    def fetch_stock_splits(self, symbol: str) -> dict[datetime, Decimal]:
        ticker = yf.Ticker(symbol)
        splits = ticker.get_splits()
        return {
            timestamp.to_pydatetime().astimezone(timezone.utc): Decimal(str(value))
            for timestamp, value in splits.items()
        }

    def _fetch_prices(
        self,
        symbols: list[str],
        interval: str,
        period: str | None = None,
        start: date | datetime | None = None,
        end: date | datetime | None = None,
        extended_hours: bool = False,
    ) -> dict[str, Decimal | None]:
        data: pd.DataFrame = yf.download(
            symbols,
            interval=interval,
            period=period,
            start=start,
            end=end,
            prepost=extended_hours,
            group_by="ticker",
        )
        prices: dict[str, Decimal | None] = {symbol: None for symbol in symbols}

        if data.empty:
            return prices

        for symbol in symbols:
            try:
                symbol_data = cast(pd.DataFrame, data[symbol.upper()])
            except KeyError:
                prices[symbol] = None
            else:
                prices[symbol] = self._get_last_available_price(symbol_data)

        return prices

    def _get_last_available_price(self, data: pd.DataFrame) -> Decimal | None:
        prices = data["Close"].dropna()
        if prices.empty:
            return None

        price = prices.iloc[-1]
        return Decimal(str((price)))
