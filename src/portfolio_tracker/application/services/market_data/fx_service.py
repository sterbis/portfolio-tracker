from datetime import date, datetime, timezone

from portfolio_tracker.application.ports.clients import FxClient, FxClientError
from portfolio_tracker.application.ports.unit_of_work import UnitOfWork
from portfolio_tracker.domain.market_data import FxRates


class FxService:
    def __init__(
        self,
        app_base_currency: str,
        app_supported_currencies: set[str],
        fx_client: FxClient,
    ):
        self._app_base_currency = app_base_currency
        self._app_supported_currencies = app_supported_currencies
        self._fx_client = fx_client

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

    def fetch_rates(self, dates: set[date]) -> list[FxRates]:
        fetched_rates: list[FxRates] = []
        not_fetched_dates: set[date] = set()

        for date_ in dates:
            try:
                rates = self._fx_client.fetch_historical_rates(
                    self._app_base_currency,
                    date_,
                    self._app_supported_currencies,
                )
                fetched_rates.append(rates)
            except FxClientError:
                not_fetched_dates.add(date_)

        if not_fetched_dates:
            formatted_dates = ", ".join(
                date_.isoformat() for date_ in sorted(not_fetched_dates)
            )
            raise FxDataIntegrityError(
                "Data Integrity Violation: Failed to sync historical FX rates "
                f" for following dates: {formatted_dates}."
            )

        return fetched_rates

    def _get_fallback_spot_rates(self, today: date, uow: UnitOfWork) -> FxRates:
        max_allowed_lag_days = 3 if today.weekday() in (5, 6, 0) else 1

        with uow:
            rates = uow.fx_rates.get_latest()

        if not rates:
            raise FxDataIntegrityError(
                "Data Integrity Violation: No FX rates exist in repository."
            )

        lag_days = (today - rates.effective_on).days

        if lag_days > max_allowed_lag_days:
            raise FxDataIntegrityError(
                "Data Integrity Violation: Cannot provide fallback rates for faild API call. "
                f"Latest repository rates ({rates.effective_on}) are too stale ({lag_days} days old)."
            )

        return rates


class FxDataIntegrityError(Exception):
    pass
