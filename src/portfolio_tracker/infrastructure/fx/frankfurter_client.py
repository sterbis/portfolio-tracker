import json
from collections import defaultdict
from collections.abc import Iterator
from datetime import date, datetime, timezone
from decimal import Decimal

import requests

from portfolio_tracker.application.fx import FxClient, FxClientError
from portfolio_tracker.domain.fx import FxRates


class FrankfurterClient(FxClient):
    _BASE_URL = "https://api.frankfurter.dev/v2/"

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
        return self._fetch_rates(base_currency, quote_currencies)
    
    def fetch_rates_series(
        self,
        base_currency: str,
        quote_currencies: set[str],
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

        required_base_currency = base_currency.upper()
        required_quote_currencies = {currency.upper() for currency in quote_currencies}
        required_dates = {date.isoformat() for date in only_dates} if only_dates else set()

        buffer: dict[str, dict[str, str]] = defaultdict(dict)

        for line in response.iter_lines(decode_unicode=True):
            data: dict[str, str] = json.loads(line)

            date_ = data["date"]
            base_currency = data["base"].upper()
            quote_currency = data["quote"].upper()
            rate = str(data["rate"])

            if required_dates and date_ not in required_dates:
                continue

            if base_currency != required_base_currency:
                raise FxClientError(
                    f"Unexpected base currency data returned."
                    f"Requested: {required_base_currency}, got: {base_currency}."
                )

            buffer[date_][quote_currency] = rate

            if buffer[date_].keys() == required_quote_currencies:
                yield FxRates(
                    effective_on=date.fromisoformat(date_),
                    base_currency=base_currency,
                    base_rates={
                        quote_currency: Decimal(rate)
                        for quote_currency, rate in buffer.pop(date_).items()
                    },
                )

        for date_, rates in buffer.items():
            yield FxRates(
                effective_on=date.fromisoformat(date_),
                base_currency=base_currency,
                base_rates={
                    quote_currency: Decimal(rate)
                    for quote_currency, rate in rates.items()
                },
            )

    def _fetch_rates(
        self,
        base_currency: str,
        quote_currencies: set[str],
        date_: date | None = None,
    ) -> FxRates:
        response = self._fetch(
            base_currency,
            quote_currencies,
            date_=date_,
        )
        return FxRates(
            effective_on=date_ or datetime.now(tz=timezone.utc).date(),
            base_currency=base_currency.upper(),
            base_rates={
                data["quote"].upper(): Decimal(str(data["rate"]))
                for data in response.json()
            },
        )

    def _fetch(
        self,
        base_currency: str,
        quote_currencies: set[str],
        date_: date | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        headers: dict[str, str] | None = None,
        stream: bool = False,
    ) -> requests.Response:
        url = f"{self._BASE_URL}rates"
        headers = headers or {"Accept": "application/json"}
        parameters = {
            "base": base_currency,
            "quotes": ",".join(quote_currencies),
        }
        if date_:
            parameters["date"] = date_.isoformat()

        if from_date:
            parameters["from"] = from_date.isoformat()

        if to_date:
            parameters["to"] = to_date.isoformat()

        try:
            response = requests.get(
                url, params=parameters, headers=headers, stream=stream, timeout=5
            )
            response.raise_for_status()
            return response

        except requests.HTTPError as error:
            raise FxClientError(
                f"FX client API request '{url}' failed: {response.status_code} {response.reason}"
            ) from error

        except Exception as error:
            raise FxClientError(
                f"FX client API request '{url}' failed: '{error}'"
            ) from error
