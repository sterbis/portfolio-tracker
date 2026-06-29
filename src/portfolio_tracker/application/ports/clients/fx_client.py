from abc import ABC, abstractmethod
from datetime import date

from portfolio_tracker.domain.market_data import FxRates


class FxClient(ABC):
    @abstractmethod
    def fetch_historical_rates(
        self,
        base_currency: str,
        effective_on: date,
        currencies: set[str] | None = None,
    ) -> FxRates: ...

    @abstractmethod
    def fetch_spot_rates(
        self,
        base_currency: str,
        currencies: set[str] | None = None,
    ) -> FxRates: ...


class FxClientError(Exception): ...
