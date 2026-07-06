from datetime import date, datetime, timezone
from decimal import Decimal

import requests

from portfolio_tracker.application.fx import FxClient, FxClientError
from portfolio_tracker.domain.fx import FxRates


class FrankfurterClient(FxClient):
    BASE_URL = "https://api.frankfurter.dev/v2"

    def fetch_historical_rates(
        self,
        base_currency: str,
        quote_currencies: set[str],
        date_: date,
    ) -> FxRates:
        return self._fetch_rates(base_currency, quote_currencies, date_)

    def fetch_spot_rates(
        self,
        base_currency: str,
        quote_currencies: set[str],
    ) -> FxRates:
        date_ = datetime.now(tz=timezone.utc).date()
        return self._fetch_rates(base_currency, quote_currencies, date_)

    def _fetch_rates(
        self,
        base_currency: str,
        quote_currencies: set[str],
        date_: date,
    ) -> FxRates:
        url = f"{self.BASE_URL}/rates"
        parameters = {
            "date": date_.isoformat(),
            "base": base_currency,
            "quotes": ",".join(quote_currencies),
        }

        try:
            response = requests.get(url, params=parameters, timeout=5)
            response.raise_for_status()

        except requests.exceptions.RequestException as error:
            raise FxClientError(
                f"FX client request '{response.request.url}' failed: '{error}'"
            ) from error

        data = response.json()
        if not data or not isinstance(data, list):
            raise FxClientError(
                f"No or unexpected data returned for FX client request: '{response.request.url}'."
            )
        
        for currency_pair_data in data:
            if currency_pair_data.base.upper() != base_currency.upper():
                raise FxClientError(
                    f"Unexpected base currency data returned for FX client request: '{response.request.url}'."
                    f"Requested: {base_currency}, got: {currency_pair_data.base}."
                )

        return FxRates(
            effective_on=date_,
            base_currency=base_currency.upper(),
            base_rates={
                currency_pair_data.quote.upper(): Decimal(str(currency_pair_data.rate))
                for currency_pair_data in data
            },
        )
