from decimal import Decimal

import pytest

from portfolio_tracker.domain.shared import DualMoney, Money


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
