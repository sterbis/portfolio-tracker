from datetime import date
from decimal import Decimal
import pytest

from portfolio_tracker.domain.market_data import FxRates


def test_fx_rates_conversions() -> None:
    # Base currency USD
    rates = FxRates(
        effective_on=date(2026, 1, 1),
        base_currency="USD",
        base_rates={
            "EUR": Decimal("0.90"),
            "CZK": Decimal("23.00"),
        },
    )

    # Identical currency conversion
    assert rates.get_rate("USD", "USD") == Decimal("1.0")

    # Base to quote currency conversion
    assert rates.get_rate("USD", "EUR") == Decimal("0.90")

    # Quote to base currency conversion
    assert rates.get_rate("EUR", "USD") == Decimal(
        "1.11111111"
    )  # 1 / 0.90 rounded half up

    # Quote to quote currency conversion (triangulation)
    # EUR to CZK = CZK rate / EUR rate = 23 / 0.9 = 25.55555556
    assert rates.get_rate("EUR", "CZK") == Decimal("25.55555556")


def test_fx_rates_missing_currency_raises_value_error() -> None:
    rates = FxRates(
        effective_on=date(2026, 1, 1),
        base_currency="USD",
        base_rates={"EUR": Decimal("0.90")},
    )

    with pytest.raises(
        ValueError, match="Exchange rate for USD/GBP currency pair not available"
    ):
        _ = rates.get_rate("USD", "GBP")
