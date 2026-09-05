from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from portfolio_tracker.domain.shared import Currency


@dataclass(frozen=True)
class FxRates:
    effective_on: date
    base_currency: Currency
    rates: dict[Currency, Decimal]

    def get_rate(self, base_currency: Currency, quote_currency: Currency) -> Decimal:
        if base_currency == quote_currency:
            return Decimal("1.0")

        if base_currency == self.base_currency:
            return self._get(quote_currency)

        if quote_currency == self.base_currency:
            rate = Decimal("1.0") / self._get(base_currency)
            return rate.quantize(Decimal("1.00000000"), rounding=ROUND_HALF_UP)

        rate = self._get(quote_currency) / self._get(base_currency)
        return rate.quantize(Decimal("1.00000000"), rounding=ROUND_HALF_UP)

    def _get(self, currency: Currency) -> Decimal:
        try:
            return self.rates[currency]
        except KeyError as error:
            raise ValueError(
                f"Exchange rate for {self.base_currency}/{currency} "
                f"currency pair not available on date {self.effective_on}."
            ) from error
