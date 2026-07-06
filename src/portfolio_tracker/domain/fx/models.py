from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class FxRates:
    effective_on: date
    base_currency: str
    base_rates: dict[str, Decimal]

    def get_rate(self, base_currency: str, quote_currency: str) -> Decimal:
        if base_currency == quote_currency:
            return Decimal("1.0")

        if base_currency == self.base_currency:
            return self._lookup_base_rate(quote_currency)

        if quote_currency == self.base_currency:
            rate = Decimal("1.0") / self._lookup_base_rate(base_currency)
            return rate.quantize(Decimal("1.00000000"), rounding=ROUND_HALF_UP)

        rate = self._lookup_base_rate(quote_currency) / self._lookup_base_rate(
            base_currency
        )
        return rate.quantize(Decimal("1.00000000"), rounding=ROUND_HALF_UP)

    def _lookup_base_rate(self, currency: str) -> Decimal:
        try:
            return self.base_rates[currency]
        except KeyError as error:
            raise ValueError(
                f"Exchange rate for {self.base_currency}/{currency} "
                f"currency pair not available on date {self.effective_on}."
            ) from error
