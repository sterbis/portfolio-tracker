from datetime import date
from decimal import Decimal

import pytest

from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.shared import Currency


def test_fx_rates_conversions(sample_rates: FxRates) -> None:
    # Identical currency conversion
    assert sample_rates.get_rate(Currency.USD, Currency.USD) == Decimal("1.0")

    # Base to quote currency conversion
    assert sample_rates.get_rate(Currency.USD, Currency.EUR) == Decimal("0.90")

    # Quote to base currency conversion
    assert sample_rates.get_rate(Currency.EUR, Currency.USD) == Decimal(
        "1.11111111"
    )  # 1 / 0.90 rounded half up

    # Quote to quote currency conversion (triangulation)
    # EUR to CZK = CZK rate / EUR rate = 23 / 0.9 = 25.55555556
    assert sample_rates.get_rate(Currency.EUR, Currency.CZK) == Decimal("25.55555556")


def test_fx_rates_missing_currency_raises_value_error() -> None:
    rates = FxRates(
        effective_on=date(2026, 6, 1),
        base_currency=Currency.USD,
        rates={Currency.EUR: Decimal("0.90")},
    )

    with pytest.raises(
        ValueError, match="Exchange rate for USD/CZK currency pair not available"
    ):
        _ = rates.get_rate(Currency.USD, Currency.CZK)
