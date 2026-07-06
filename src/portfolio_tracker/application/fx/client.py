from abc import ABC, abstractmethod
from datetime import date

from portfolio_tracker.domain.fx import FxRates


class FxClient(ABC):
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


class FxClientError(Exception): ...
