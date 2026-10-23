import logging

from collections.abc import Iterator
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from portfolio_tracker.application.shared.errors import (
    FxClientError,
    FxDataIntegrityError,
)
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.shared import Currency

from .client import FxClient

if TYPE_CHECKING:
    from portfolio_tracker.application.persistence import UnitOfWork

logger = logging.getLogger(__name__)

class FxService:
    def __init__(
        self,
        base_currency: Currency,
        quote_currencies: set[Currency],
        fx_client: FxClient,
        spot_rates_cache_ttl: int = 60 * 60 * 24,
    ):
        self._base_currency = base_currency
        self._quote_currencies = quote_currencies
        self._fx_client = fx_client
        self._spot_rates_cache_ttl = spot_rates_cache_ttl
        self._cached_spot_rates: FxRates | None = None
        self._last_spot_rates_fetch_at: datetime | None = None

    @property
    def base_currency(self) -> Currency:
        return self._base_currency

    @property
    def quote_currencies(self) -> set[Currency]:
        return self._quote_currencies

    @property
    def cached_spot_rates(self) -> FxRates | None:
        if self._cached_spot_rates is None or self._last_spot_rates_fetch_at is None:
            return None

        now = datetime.now(tz=timezone.utc)
        age = (now - self._last_spot_rates_fetch_at).total_seconds()
        if age > self._spot_rates_cache_ttl:
            return None

        return self._cached_spot_rates

    def get_spot_rates(self, uow: UnitOfWork | None = None) -> FxRates:
        if cached_spot_rates := self._cached_spot_rates:
            return cached_spot_rates

        now = datetime.now(tz=timezone.utc)
        try:
            rates = self._fx_client.fetch_spot_rates(
                self._base_currency, self._quote_currencies
            )
        except FxClientError as error:
            logger.warning("Failed to fetch FX rates: %s", error)
            if not uow:
                raise

            rates = self._get_fallback_spot_rates(now.date(), uow)

        self._cached_spot_rates = rates
        self._last_spot_rates_fetch_at = now
        return rates

    def get_rates_series(
        self, from_date: date, to_date: date, only_dates: set[date] | None = None
    ) -> Iterator[FxRates]:
        return self._fx_client.fetch_rates_series(
            self._base_currency,
            self._quote_currencies,
            from_date=from_date,
            to_date=to_date,
            only_dates=only_dates,
        )

    def _get_fallback_spot_rates(self, today: date, uow: UnitOfWork) -> FxRates:
        max_allowed_lag_days = 3 if today.weekday() in (5, 6, 0) else 1

        with uow:
            rates = uow.fx_rates.get_latest()

        if not rates:
            raise FxDataIntegrityError(detail="No FX rates exist in repository.")

        lag_days = (today - rates.effective_on).days

        if lag_days > max_allowed_lag_days:
            raise FxClientError(
                "Cannot provide fallback rates for faild fetch. "
                f"Latest repository rates ({rates.effective_on}) are too stale ({lag_days} days old)."
            )

        return rates
