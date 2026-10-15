import json
from collections.abc import Iterator
from datetime import date, datetime, timezone
from decimal import Decimal

import requests

from portfolio_tracker.application.fx import FxClient
from portfolio_tracker.application.shared.errors import FxClientError
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.shared.requests_utils import (
    ApiEndpoint,
    HttpMethod,
    sync_request,
)


class FranfurterApiEndpoints:
    RATES = ApiEndpoint(
        path="/rates",
        method=HttpMethod.GET,
    )


class FrankfurterClient(FxClient):
    _BASE_URL = "https://api.frankfurter.dev/v2/"

    def fetch_historical_rates(
        self,
        base_currency: Currency,
        quote_currencies: set[Currency],
        date_: date,
    ) -> FxRates:
        return self._fetch_rates(base_currency, quote_currencies, date_)

    def fetch_spot_rates(
        self,
        base_currency: Currency,
        quote_currencies: set[Currency],
    ) -> FxRates:
        return self._fetch_rates(base_currency, quote_currencies)

    def fetch_rates_series(
        self,
        base_currency: Currency,
        quote_currencies: set[Currency],
        from_date: date,
        to_date: date,
        only_dates: set[date] | None = None,
    ) -> Iterator[FxRates]:
        response = self._fetch(
            base_currency,
            quote_currencies,
            from_date=from_date,
            to_date=to_date,
            headers={"Accept": "application/x-ndjson"},
            stream=True,
        )

        try:
            yield from self._process_response_stream(
                response,
                required_base_currency=base_currency.value.upper(),
                required_quote_currencies={
                    currency.value.upper() for currency in quote_currencies
                },
                required_dates=(
                    {date.isoformat() for date in only_dates} if only_dates else set()
                ),
            )

        except requests.exceptions.RequestException as error:
            raise FxClientError(
                "Connection interrupted while streaming FX rates."
            ) from error

        except json.JSONDecodeError as error:
            raise FxClientError("Corrupted JSON data received from FX API.") from error

        finally:
            response.close()

    def _process_response_stream(
        self,
        response: requests.Response,
        required_base_currency: str,
        required_quote_currencies: set[str],
        required_dates: set[str],
    ) -> Iterator[FxRates]:
        if not required_dates:
            return

        sorted_required_dates = sorted(required_dates)
        required_date = sorted_required_dates[0]
        latest_rates: dict[str, str] = {}
        rates_verified: bool = False

        for line in response.iter_lines(decode_unicode=True):
            data: dict[str, str] = json.loads(line)

            date_ = data["date"]
            base_currency = data["base"].upper()
            quote_currency = data["quote"].upper()
            rate = str(data["rate"])

            if base_currency != required_base_currency:
                raise FxClientError(
                    f"Unexpected base currency data returned."
                    f"Requested: {required_base_currency}, got: {base_currency}."
                )

            latest_rates[quote_currency] = rate

            while date_ > required_date:
                if not rates_verified:
                    self._verify_available_rates(
                        set(latest_rates), required_quote_currencies, required_date
                    )
                    rates_verified = True

                yield FxRates(
                    effective_on=date.fromisoformat(required_date),
                    base_currency=Currency(base_currency),
                    rates={
                        Currency(quote_currency): Decimal(rate)
                        for quote_currency, rate in latest_rates.items()
                    },
                )
                sorted_required_dates.pop(0)
                if not sorted_required_dates:
                    return

                required_date = sorted_required_dates[0]

        if not rates_verified:
            self._verify_available_rates(
                set(latest_rates), required_quote_currencies, required_date
            )

        for required_date in sorted_required_dates:
            yield FxRates(
                effective_on=date.fromisoformat(required_date),
                base_currency=Currency(required_base_currency),
                rates={
                    Currency(quote_currency): Decimal(rate)
                    for quote_currency, rate in latest_rates.items()
                },
            )

    def _verify_available_rates(
        self,
        quote_currencies: set[str],
        required_quote_currencies: set[str],
        date_: str,
    ) -> None:
        if missing_currencies := required_quote_currencies - quote_currencies:
            raise FxClientError(
                f"Missing FX rates for quote currencies {', '.join(missing_currencies)} on date {date_}"
            )

    def _fetch_rates(
        self,
        base_currency: Currency,
        quote_currencies: set[Currency],
        date_: date | None = None,
    ) -> FxRates:
        response = self._fetch(
            base_currency,
            quote_currencies,
            date_=date_,
        )
        return FxRates(
            effective_on=date_ or datetime.now(tz=timezone.utc).date(),
            base_currency=Currency(base_currency.upper()),
            rates={
                Currency(data["quote"].upper()): Decimal(str(data["rate"]))
                for data in response.json()
            },
        )

    def _fetch(
        self,
        base_currency: Currency,
        quote_currencies: set[Currency],
        date_: date | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        headers: dict[str, str] | None = None,
        stream: bool = False,
    ) -> requests.Response:
        url = f"{self._BASE_URL}rates"
        headers = headers or {"Accept": "application/json"}
        parameters = {
            "base": base_currency.value,
            "quotes": ",".join(
                quote_currency.value for quote_currency in quote_currencies
            ),
        }
        if date_:
            parameters["date"] = date_.isoformat()

        if from_date:
            parameters["from"] = from_date.isoformat()

        if to_date:
            parameters["to"] = to_date.isoformat()

        try:
            return sync_request(
                FranfurterApiEndpoints.RATES,
                base_url=self._BASE_URL,
                params=parameters,
                headers=headers,
                stream=stream,
                timeout=5,
            )

        except Exception as error:
            raise FxClientError(f"FX API request '{url}' failed: '{error}'") from error
