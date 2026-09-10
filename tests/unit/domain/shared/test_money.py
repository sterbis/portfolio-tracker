from decimal import Decimal

import pytest

from portfolio_tracker.domain.shared import Currency, DualMoney, Money


def test_money_basic_arithmetic() -> None:
    m1 = Money(Decimal("100.50"), Currency.USD)
    m2 = Money(Decimal("50.25"), Currency.USD)

    # Addition
    assert m1 + m2 == Money(Decimal("150.75"), Currency.USD)

    # Subtraction
    assert m1 - m2 == Money(Decimal("50.25"), Currency.USD)

    # Negation
    assert -m1 == Money(Decimal("-100.50"), Currency.USD)

    # Multiplication
    assert m1 * 2 == Money(Decimal("201.00"), Currency.USD)
    assert 3 * m1 == Money(Decimal("301.50"), Currency.USD)
    assert m1 * Decimal("1.5") == Money(Decimal("150.75"), Currency.USD)

    # Division
    assert m1 / 2 == Money(Decimal("50.25"), Currency.USD)
    assert m1 / Decimal("0.5") == Money(Decimal("201.00"), Currency.USD)


def test_money_comparisons() -> None:
    m1 = Money(Decimal("100"), Currency.USD)
    m2 = Money(Decimal("200"), Currency.USD)

    assert m1 < m2
    assert m2 > m1
    assert m1 <= m2
    assert m1 != m2
    assert m1 == Money(Decimal("100"), Currency.USD)


def test_money_mismatched_currency_raises_error() -> None:
    m_usd = Money(Decimal("100"), Currency.USD)
    m_eur = Money(Decimal("100"), Currency.EUR)

    with pytest.raises(ValueError, match="Currency mismatch"):
        _ = m_usd + m_eur

    with pytest.raises(ValueError, match="Currency mismatch"):
        _ = m_usd - m_eur

    with pytest.raises(ValueError, match="Currency mismatch"):
        _ = m_usd < m_eur


def test_money_invalid_multiplication_operand() -> None:
    m = Money(Decimal("100"), Currency.USD)
    with pytest.raises(TypeError):
        _ = m * "invalid"  # type: ignore[operator]


def test_dual_money_arithmetic() -> None:
    dm1 = DualMoney(
        Money(Decimal("10"), Currency.USD), Money(Decimal("200"), Currency.CZK)
    )
    dm2 = DualMoney(
        Money(Decimal("5"), Currency.USD), Money(Decimal("100"), Currency.CZK)
    )

    # Addition
    assert dm1 + dm2 == DualMoney(
        Money(Decimal("15"), Currency.USD), Money(Decimal("300"), Currency.CZK)
    )

    # Subtraction
    assert dm1 - dm2 == DualMoney(
        Money(Decimal("5"), Currency.USD), Money(Decimal("100"), Currency.CZK)
    )

    # Multiplication
    assert dm1 * 2 == DualMoney(
        Money(Decimal("20"), Currency.USD), Money(Decimal("400"), Currency.CZK)
    )
    assert 3 * dm1 == DualMoney(
        Money(Decimal("30"), Currency.USD), Money(Decimal("600"), Currency.CZK)
    )

    # Division
    assert dm1 / 2 == DualMoney(
        Money(Decimal("5"), Currency.USD), Money(Decimal("100"), Currency.CZK)
    )
