from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal


class MarketDataClient(ABC):
    @abstractmethod
    def fetch_historical_prices(
        self, symbols: set[str], date_: date
    ) -> dict[str, Decimal | None]: ...

    @abstractmethod
    def fetch_spot_prices(
        self, symbols: set[str], extended_hours: bool = False
    ) -> dict[str, Decimal | None]: ...

    @abstractmethod
    def fetch_stock_splits(
        self, symbol: str
    ) -> dict[datetime, Decimal]: ...


class MarketDataClientError(Exception): ...
