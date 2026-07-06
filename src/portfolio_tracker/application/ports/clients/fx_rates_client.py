from abc import ABC, abstractmethod
from datetime import date

from portfolio_tracker.domain.market_data import FxRates


class FxRatesClient(ABC):
    @abstractmethod
    def fetch_historical_rates(
        self,
        base_currency: str,
        quote_currencies: set[str],
        date_: date,
    ) -> FxRates: ...

    @abstractmethod
    def fetch_spot_rates(
        self,
        base_currency: str,
        quote_currencies: set[str],
    ) -> FxRates: ...


class FxRatesClientError(Exception): ...
