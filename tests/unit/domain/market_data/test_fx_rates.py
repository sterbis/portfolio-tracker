from decimal import Decimal
import pytest

from portfolio_tracker.domain.market_data import FxRates


def test_fx_rates_conversions(sample_rates: FxRates) -> None:
    # Identical currency conversion
    assert sample_rates.get_rate("USD", "USD") == Decimal("1.0")

    # Base to quote currency conversion
    assert sample_rates.get_rate("USD", "EUR") == Decimal("0.90")

    # Quote to base currency conversion
    assert sample_rates.get_rate("EUR", "USD") == Decimal(
        "1.11111111"
    )  # 1 / 0.90 rounded half up

    # Quote to quote currency conversion (triangulation)
    # EUR to CZK = CZK rate / EUR rate = 23 / 0.9 = 25.55555556
    assert sample_rates.get_rate("EUR", "CZK") == Decimal("25.55555556")


def test_fx_rates_missing_currency_raises_value_error(sample_rates: FxRates) -> None:
    with pytest.raises(
        ValueError, match="Exchange rate for USD/GBP currency pair not available"
    ):
        _ = sample_rates.get_rate("USD", "GBP")
