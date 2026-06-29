from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest

from portfolio_tracker.domain.ledger.transaction import Transaction, TransactionType
from portfolio_tracker.domain.shared.money import Money


def test_valid_buy_transaction() -> None:
    # A valid BUY transaction
    tx = Transaction(
        correlation_id="corr_123",
        executed_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        asset_account_id="acc_abc",
        type=TransactionType.BUY,
        instrument_id="inst_123",
        quantity=Decimal("10.5"),
        price=Money(Decimal("150.0"), "USD"),
        fee=Money(Decimal("1.5"), "USD"),
        tax=Money(Decimal("0.5"), "USD"),
        cash_impact=Money(Decimal("-1576.5"), "USD"),
    )
    assert tx.id.startswith("tr_")
    assert tx.correlation_id == "corr_123"


def test_valid_deposit_without_instrument() -> None:
    # A deposit does not require an instrument_id
    tx = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        asset_account_id="acc_abc",
        type=TransactionType.DEPOSIT,
        instrument_id=None,
        quantity=Decimal("0.0"),
        price=Money(Decimal("0.0"), "USD"),
        fee=Money(Decimal("0.0"), "USD"),
        tax=Money(Decimal("0.0"), "USD"),
        cash_impact=Money(Decimal("1000.0"), "USD"),
    )
    assert tx.id.startswith("tr_")
    assert tx.instrument_id is None


def test_naive_datetime_raises_value_error() -> None:
    with pytest.raises(ValueError, match="represented in UTC time zone"):
        Transaction(
            correlation_id=None,
            executed_at=datetime(2026, 1, 1, 10, 0),  # Naive
            asset_account_id="acc_abc",
            type=TransactionType.DEPOSIT,
            instrument_id=None,
            quantity=Decimal("0.0"),
            price=Money(Decimal("0.0"), "USD"),
            fee=Money(Decimal("0.0"), "USD"),
            tax=Money(Decimal("0.0"), "USD"),
            cash_impact=Money(Decimal("1000.0"), "USD"),
        )


def test_non_utc_timezone_raises_value_error() -> None:
    est = timezone(timedelta(hours=-5))
    with pytest.raises(ValueError, match="represented in UTC time zone"):
        Transaction(
            correlation_id=None,
            executed_at=datetime(2026, 1, 1, 10, 0, tzinfo=est),  # Non-UTC
            asset_account_id="acc_abc",
            type=TransactionType.DEPOSIT,
            instrument_id=None,
            quantity=Decimal("0.0"),
            price=Money(Decimal("0.0"), "USD"),
            fee=Money(Decimal("0.0"), "USD"),
            tax=Money(Decimal("0.0"), "USD"),
            cash_impact=Money(Decimal("1000.0"), "USD"),
        )


def test_buy_without_instrument_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Instrument not provided"):
        Transaction(
            correlation_id=None,
            executed_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            asset_account_id="acc_abc",
            type=TransactionType.BUY,
            instrument_id=None,  # Missing for BUY
            quantity=Decimal("10.0"),
            price=Money(Decimal("10.0"), "USD"),
            fee=Money(Decimal("0.0"), "USD"),
            tax=Money(Decimal("0.0"), "USD"),
            cash_impact=Money(Decimal("-100.0"), "USD"),
        )


def test_negative_quantity_raises_value_error() -> None:
    with pytest.raises(ValueError, match="quantity cannot be negative"):
        Transaction(
            correlation_id=None,
            executed_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            asset_account_id="acc_abc",
            type=TransactionType.BUY,
            instrument_id="inst_123",
            quantity=Decimal("-1.0"),  # Negative quantity
            price=Money(Decimal("10.0"), "USD"),
            fee=Money(Decimal("0.0"), "USD"),
            tax=Money(Decimal("0.0"), "USD"),
            cash_impact=Money(Decimal("-10.0"), "USD"),
        )


def test_negative_price_raises_value_error() -> None:
    with pytest.raises(ValueError, match="price cannot be negative"):
        Transaction(
            correlation_id=None,
            executed_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            asset_account_id="acc_abc",
            type=TransactionType.BUY,
            instrument_id="inst_123",
            quantity=Decimal("1.0"),
            price=Money(Decimal("-5.0"), "USD"),  # Negative price
            fee=Money(Decimal("0.0"), "USD"),
            tax=Money(Decimal("0.0"), "USD"),
            cash_impact=Money(Decimal("5.0"), "USD"),
        )
