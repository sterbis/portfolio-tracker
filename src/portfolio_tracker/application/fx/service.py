from collections.abc import Iterator
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from portfolio_tracker.domain.fx import FxRates

from .client import FxClient
from .exceptions import FxClientError, FxDataIntegrityError

if TYPE_CHECKING:
    from portfolio_tracker.application.persistence import UnitOfWork


class FxService:
    def __init__(
        self,
        fx_client: FxClient,
        app_base_currency: str,
        app_supported_currencies: set[str],
    ):
        self._fx_client = fx_client
        self._app_base_currency = app_base_currency
        self._app_supported_currencies = app_supported_currencies

        self._cached_spot_rates: FxRates | None = None
        self._cached_spot_rates_ttl: int = 300
        self._spot_rates_fetched_at: datetime | None = None

    def get_spot_rates(self, uow: UnitOfWork | None = None) -> FxRates:
        now = datetime.now(timezone.utc)

        if self._cached_spot_rates and self._spot_rates_fetched_at:
            age = (now - self._spot_rates_fetched_at).total_seconds()
            if age < self._cached_spot_rates_ttl:
                return self._cached_spot_rates

        try:
            rates = self._fx_client.fetch_spot_rates(
                self._app_base_currency,
                self._app_supported_currencies,
            )

        except FxClientError:
            if not uow:
                raise

            rates = self._get_fallback_spot_rates(now.date(), uow)

        self._cached_spot_rates = rates
        self._spot_rates_fetched_at = now
        return rates

    def get_rates_series(self, from_date: date, to_date: date) -> Iterator[FxRates]:
        try:
            return self._fx_client.fetch_rates_series(
                self._app_base_currency,
                self._app_supported_currencies,
                from_date=from_date,
                to_date=to_date,
            )

        except FxClientError as error:
            raise FxDataIntegrityError(
                detail=f"Failed to fetch FX rates series from {from_date} to {to_date}."
            ) from error

    def _get_fallback_spot_rates(self, today: date, uow: UnitOfWork) -> FxRates:
        max_allowed_lag_days = 3 if today.weekday() in (5, 6, 0) else 1

        with uow:
            rates = uow.fx_rates.get_latest()

        if not rates:
            raise FxDataIntegrityError(detail="No FX rates exist in repository.")

        lag_days = (today - rates.effective_on).days

        if lag_days > max_allowed_lag_days:
            raise FxDataIntegrityError(
                detail=(
                    "Cannot provide fallback spot rates for faild API call. "
                    f"Latest repository rates ({rates.effective_on}) are too stale ({lag_days} days old)."
                )
            )

        return rates
