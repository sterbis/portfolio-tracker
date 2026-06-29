from datetime import date
from decimal import Decimal
import pytest

from portfolio_tracker.domain.shared.money import Money, DualMoney
from portfolio_tracker.domain.market_data.fx_rates import FxRates


def test_money_basic_arithmetic() -> None:
    m1 = Money(Decimal("100.50"), "USD")
    m2 = Money(Decimal("50.25"), "USD")

    # Addition
    assert m1 + m2 == Money(Decimal("150.75"), "USD")

    # Subtraction
    assert m1 - m2 == Money(Decimal("50.25"), "USD")

    # Negation
    assert -m1 == Money(Decimal("-100.50"), "USD")

    # Multiplication
    assert m1 * 2 == Money(Decimal("201.00"), "USD")
    assert 3 * m1 == Money(Decimal("301.50"), "USD")
    assert m1 * Decimal("1.5") == Money(Decimal("150.75"), "USD")

    # Division
    assert m1 / 2 == Money(Decimal("50.25"), "USD")
    assert m1 / Decimal("0.5") == Money(Decimal("201.00"), "USD")


def test_money_comparisons() -> None:
    m1 = Money(Decimal("100"), "USD")
    m2 = Money(Decimal("200"), "USD")

    assert m1 < m2
    assert m2 > m1
    assert m1 <= m2
    assert m1 != m2
    assert m1 == Money(Decimal("100"), "USD")


def test_money_mismatched_currency_raises_error() -> None:
    m_usd = Money(Decimal("100"), "USD")
    m_eur = Money(Decimal("100"), "EUR")

    with pytest.raises(ValueError, match="Currency mismatch"):
        _ = m_usd + m_eur

    with pytest.raises(ValueError, match="Currency mismatch"):
        _ = m_usd - m_eur

    with pytest.raises(ValueError, match="Currency mismatch"):
        _ = m_usd < m_eur


def test_money_invalid_multiplication_operand() -> None:
    m = Money(Decimal("100"), "USD")
    with pytest.raises(TypeError):
        _ = m * "invalid"  # type: ignore[operator]


def test_dual_money_arithmetic() -> None:
    dm1 = DualMoney(Money(Decimal("10"), "USD"), Money(Decimal("200"), "CZK"))
    dm2 = DualMoney(Money(Decimal("5"), "USD"), Money(Decimal("100"), "CZK"))

    # Addition
    assert dm1 + dm2 == DualMoney(
        Money(Decimal("15"), "USD"), Money(Decimal("300"), "CZK")
    )

    # Subtraction
    assert dm1 - dm2 == DualMoney(
        Money(Decimal("5"), "USD"), Money(Decimal("100"), "CZK")
    )

    # Multiplication
    assert dm1 * 2 == DualMoney(
        Money(Decimal("20"), "USD"), Money(Decimal("400"), "CZK")
    )
    assert 3 * dm1 == DualMoney(
        Money(Decimal("30"), "USD"), Money(Decimal("600"), "CZK")
    )

    # Division
    assert dm1 / 2 == DualMoney(
        Money(Decimal("5"), "USD"), Money(Decimal("100"), "CZK")
    )


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
