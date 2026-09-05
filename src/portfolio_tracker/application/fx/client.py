from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import date

from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.shared import Currency


class FxClient(ABC):
    @abstractmethod
    def fetch_historical_rates(
        self,
        base_currency: Currency,
        quote_currencies: set[Currency],
        date_: date,
    ) -> FxRates: ...

    @abstractmethod
    def fetch_spot_rates(
        self,
        base_currency: Currency,
        quote_currencies: set[Currency],
    ) -> FxRates: ...

    @abstractmethod
    def fetch_rates_series(
        self,
        base_currency: Currency,
        quote_currencies: set[Currency],
        from_date: date,
        to_date: date,
        only_dates: set[date] | None = None,
    ) -> Iterator[FxRates]: ...
