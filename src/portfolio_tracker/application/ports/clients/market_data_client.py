from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal


class MarketDataClient(ABC):
    @abstractmethod
    def fetch_historical_prices(
        self, symbols: set[str], effective_on: date
    ) -> dict[str, Decimal]: ...

    @abstractmethod
    def fetch_spot_prices(self, symbols: set[str]) -> dict[str, Decimal]: ...

    @abstractmethod
    def fetch_stock_splits(
        self, symbols: set[str]
    ) -> dict[str, dict[datetime, Decimal]]: ...


class MarketDataClientError(Exception): ...
