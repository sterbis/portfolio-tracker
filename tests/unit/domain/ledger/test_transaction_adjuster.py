from datetime import datetime, timezone
from decimal import Decimal
from portfolio_tracker.domain.ledger.transaction import Transaction, TransactionType
from portfolio_tracker.domain.ledger.transaction_adjuster import TransactionAdjuster
from portfolio_tracker.domain.market_data.stock_splits import StockSplits
from portfolio_tracker.domain.shared.money import Money


def test_transaction_adjuster_split_boundaries() -> None:
    adjuster = TransactionAdjuster()

    # Stock split on 2026-06-15 00:00:00 UTC (2-for-1 split, ratio = 2.0)
    split_date = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    splits_list = [
        StockSplits(
            instrument_id="inst_aapl",
            splits={split_date: Decimal("2.0")},
        )
    ]

    # Tx 1: Executed before split (should be adjusted)
    transaction_before_split = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 6, 14, 10, 0, tzinfo=timezone.utc),
        asset_account_id="acc_1",
        type=TransactionType.BUY,
        instrument_id="inst_aapl",
        quantity=Decimal("10"),
        price=Money(Decimal("100"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("-1000"), "USD"),
    )

    # Tx 2: Executed after split (should NOT be adjusted)
    transaction_after_split = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc),
        asset_account_id="acc_1",
        type=TransactionType.BUY,
        instrument_id="inst_aapl",
        quantity=Decimal("10"),
        price=Money(Decimal("100"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("-1000"), "USD"),
    )

    # Tx 3: Executed exactly on split date/time (should NOT be adjusted under current logic)
    transaction_exactly_at_split = Transaction(
        correlation_id=None,
        executed_at=split_date,
        asset_account_id="acc_1",
        type=TransactionType.BUY,
        instrument_id="inst_aapl",
        quantity=Decimal("10"),
        price=Money(Decimal("100"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("-1000"), "USD"),
    )

    # Run the adjuster
    snapshot_at = datetime(2026, 6, 20, 0, 0, tzinfo=timezone.utc)
    results = list(
        adjuster.adjust(
            transactions=[transaction_before_split, transaction_after_split, transaction_exactly_at_split],
            splits_list=splits_list,
            snapshot_at=snapshot_at,
        )
    )

    # Verify Tx before: quantity multiplied by 2, price divided by 2
    assert results[0].quantity == Decimal("20")
    assert results[0].price == Money(Decimal("50"), "USD")

    # Verify Tx after: unchanged
    assert results[1].quantity == Decimal("10")
    assert results[1].price == Money(Decimal("100"), "USD")

    # Verify Tx exactly: unchanged (since transaction.executed_at < split_datetime is required)
    assert results[2].quantity == Decimal("10")
    assert results[2].price == Money(Decimal("100"), "USD")


def test_transaction_adjuster_multiple_cumulative_splits() -> None:
    adjuster = TransactionAdjuster()

    # AAPL has two splits:
    # 1. 2026-06-15: 2-for-1 (ratio = 2.0)
    # 2. 2026-06-18: 3-for-1 (ratio = 3.0)
    splits_list = [
        StockSplits(
            instrument_id="inst_aapl",
            splits={
                datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc): Decimal("2.0"),
                datetime(2026, 6, 18, 0, 0, tzinfo=timezone.utc): Decimal("3.0"),
            },
        )
    ]

    transaction = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 6, 14, 0, 0, tzinfo=timezone.utc),
        asset_account_id="acc_1",
        type=TransactionType.BUY,
        instrument_id="inst_aapl",
        quantity=Decimal("10"),
        price=Money(Decimal("120"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("-1200"), "USD"),
    )

    snapshot_at = datetime(2026, 6, 20, 0, 0, tzinfo=timezone.utc)
    results = list(adjuster.adjust([transaction], splits_list, snapshot_at))

    # Total multiplier should be 2.0 * 3.0 = 6.0
    assert results[0].quantity == Decimal("60")
    assert results[0].price == Money(Decimal("20"), "USD")


def test_transaction_adjuster_ignores_non_trades() -> None:
    adjuster = TransactionAdjuster()

    splits_list = [
        StockSplits(
            instrument_id="inst_aapl",
            splits={datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc): Decimal("2.0")},
        )
    ]

    deposit_transaction = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 6, 14, 0, 0, tzinfo=timezone.utc),
        asset_account_id="acc_1",
        type=TransactionType.DEPOSIT,
        instrument_id=None,
        quantity=Decimal("0"),
        price=Money(Decimal("0"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("1000"), "USD"),
    )

    snapshot_at = datetime(2026, 6, 20, 0, 0, tzinfo=timezone.utc)
    results = list(adjuster.adjust([deposit_transaction], splits_list, snapshot_at))

    assert results[0] == deposit_transaction
