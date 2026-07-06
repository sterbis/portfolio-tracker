# pylint: disable=redefined-outer-name

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from portfolio_tracker.domain.account import AssetAccount
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.instrument import Stock
from portfolio_tracker.domain.portfolio.position import (
    AccountingMethod,
    PositionBuilder,
)
from portfolio_tracker.domain.shared import DualMoney, Money
from portfolio_tracker.domain.transaction import Transaction, TransactionType


@pytest.fixture
def aapl_transactions(
    aapl_stock: Stock, sample_asset_account: AssetAccount
) -> list[Transaction]:
    return [
        # Buy 10 AAPL shares @ 180
        Transaction(
            correlation_id=None,
            executed_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            asset_account_id=sample_asset_account.id,
            instrument_id=aapl_stock.id,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Money(Decimal("180"), "USD"),
            fee=Money(Decimal("0"), "USD"),
            tax=Money(Decimal("0"), "USD"),
            cash_impact=Money(Decimal("-1800"), "USD"),
        ),
        # Buy 5 AAPL shares @ 210
        Transaction(
            correlation_id=None,
            executed_at=datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc),
            asset_account_id=sample_asset_account.id,
            instrument_id=aapl_stock.id,
            type=TransactionType.BUY,
            quantity=Decimal("5"),
            price=Money(Decimal("210"), "USD"),
            fee=Money(Decimal("0"), "USD"),
            tax=Money(Decimal("0"), "USD"),
            cash_impact=Money(Decimal("-1050"), "USD"),
        ),
        # Buy 7 AAPL shares @ 200
        Transaction(
            correlation_id=None,
            executed_at=datetime(2026, 1, 3, 10, 0, tzinfo=timezone.utc),
            asset_account_id=sample_asset_account.id,
            instrument_id=aapl_stock.id,
            type=TransactionType.BUY,
            quantity=Decimal("7"),
            price=Money(Decimal("200"), "USD"),
            fee=Money(Decimal("0"), "USD"),
            tax=Money(Decimal("0"), "USD"),
            cash_impact=Money(Decimal("-1400"), "USD"),
        ),
        # Sell 12 AAPL shares @ 220
        Transaction(
            correlation_id=None,
            executed_at=datetime(2026, 1, 4, 10, 0, tzinfo=timezone.utc),
            asset_account_id=sample_asset_account.id,
            instrument_id=aapl_stock.id,
            type=TransactionType.SELL,
            quantity=Decimal("12"),
            price=Money(Decimal("220"), "USD"),
            fee=Money(Decimal("0"), "USD"),
            tax=Money(Decimal("0"), "USD"),
            cash_impact=Money(Decimal("2640"), "USD"),
        ),
    ]


@pytest.fixture(scope="module")
def rates_by_date() -> dict[date, FxRates]:
    return {
        date(2026, 1, 1): FxRates(date(2026, 1, 1), "USD", {"CZK": Decimal("20.0")}),
        date(2026, 1, 2): FxRates(date(2026, 1, 2), "USD", {"CZK": Decimal("20.5")}),
        date(2026, 1, 3): FxRates(date(2026, 1, 3), "USD", {"CZK": Decimal("21.0")}),
        date(2026, 1, 4): FxRates(date(2026, 1, 4), "USD", {"CZK": Decimal("21.5")}),
    }


def test_execute_fifo_sell(
    aapl_stock: Stock,
    aapl_transactions: list[Transaction],
    rates_by_date: dict[date, FxRates],
) -> None:
    builder = PositionBuilder(
        instrument_id=aapl_stock.id,
        native_currency="USD",
        reporting_currency="CZK",
        accounting_method=AccountingMethod.FIFO,
    )

    for transaction in aapl_transactions:
        rates = rates_by_date[transaction.executed_at.date()]
        builder.add(transaction, rates)

    # A. Check remaining volume metrics
    assert builder.quantity == Decimal("10")

    # B. Prove that Lot 1 was entirely sold, leaving exactly 2 active tracking lots
    assert len(builder.lots) == 2

    # C. Lot 2 remaining state (3 shares left @ original 210 USD, 4,305 CZK)
    assert builder.lots[0].remaining_quantity == Decimal("3")
    assert builder.lots[0].price == DualMoney(
        Money(Decimal("210"), "USD"), Money(Decimal("4305"), "CZK")
    )

    # D. Lot 3 remaining state (7 shares left @ original 200 USD, 4,200 CZK)
    assert builder.lots[1].remaining_quantity == Decimal("7")
    assert builder.lots[1].price == DualMoney(
        Money(Decimal("200"), "USD"), Money(Decimal("4200"), "CZK")
    )

    # E. Cost Basis: (3 * 210 USD) + (7 * 200 USD) = 2030 USD
    #    Cost Basis: (3 * 4,305 CZK) + (7 * 4,200 CZK) = 42,315 CZK
    assert builder.cost_basis == DualMoney(
        Money(Decimal("2030"), "USD"), Money(Decimal("42315"), "CZK")
    )


def test_execute_average_cost_sell(
    aapl_stock: Stock,
    aapl_transactions: list[Transaction],
    rates_by_date: dict[date, FxRates],
) -> None:
    builder = PositionBuilder(
        instrument_id=aapl_stock.id,
        native_currency="USD",
        reporting_currency="CZK",
        accounting_method=AccountingMethod.AVERAGE_COST,
    )

    for transaction in aapl_transactions:
        rates = rates_by_date[transaction.executed_at.date()]
        builder.add(transaction, rates)

    # A. Check remaining volume metrics
    assert builder.quantity == Decimal("10")

    # B. Prove that Lot 1 was entirely sold, leaving exactly 2 active tracking lots
    assert len(builder.lots) == 2

    # C. Verify that all remaining lots have changed to the same average price and zero fees
    expected_average_price = DualMoney(
        Money(Decimal("4250") / Decimal("22"), "USD"),  # 193.1818...
        Money(Decimal("86925") / Decimal("22"), "CZK"),  # 3,951.1363...
    )
    expected_fee = DualMoney.zero("USD", "CZK")

    for lot in builder.lots:
        assert lot.price == expected_average_price
        assert lot.fee == expected_fee

    # E. Cost Basis: (3 + 7) * (4250 USD / 22)
    #    Cost Basis: (3 + 7) * (86,925 CZK / 22)
    assert builder.cost_basis == Decimal("10") * expected_average_price


def test_position_builder_chronological_order_enforced(
    aapl_stock: Stock, sample_asset_account: AssetAccount
) -> None:
    builder = PositionBuilder(
        instrument_id=aapl_stock.id,
        native_currency="USD",
        reporting_currency="CZK",
    )
    rates = FxRates(date(2026, 1, 2), "USD", {"CZK": Decimal("20.0")})

    # Add first tx
    tx1 = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc),
        asset_account_id=sample_asset_account.id,
        instrument_id=aapl_stock.id,
        type=TransactionType.BUY,
        quantity=Decimal("5"),
        price=Money(Decimal("180"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("-900"), "USD"),
    )
    builder.add(tx1, rates)

    # Add out-of-order tx (executed before tx1)
    tx2 = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        asset_account_id=sample_asset_account.id,
        instrument_id=aapl_stock.id,
        type=TransactionType.BUY,
        quantity=Decimal("5"),
        price=Money(Decimal("180"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("-900"), "USD"),
    )
    with pytest.raises(
        ValueError, match="Tracked transactions must be sorted by datetime"
    ):
        builder.add(tx2, rates)


def test_position_builder_instrument_mismatch_raises_error(
    aapl_stock: Stock, sample_asset_account: AssetAccount
) -> None:
    builder = PositionBuilder(
        instrument_id=aapl_stock.id,
        native_currency="USD",
        reporting_currency="CZK",
    )
    rates = FxRates(date(2026, 1, 1), "USD", {"CZK": Decimal("20.0")})

    tx = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        asset_account_id=sample_asset_account.id,
        instrument_id="MSFT",  # Mismatched instrument
        type=TransactionType.BUY,
        quantity=Decimal("5"),
        price=Money(Decimal("180"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("-900"), "USD"),
    )
    with pytest.raises(ValueError, match="Invalid transaction instrument"):
        builder.add(tx, rates)


def test_position_builder_short_selling_protection(
    aapl_stock: Stock, sample_asset_account: AssetAccount
) -> None:
    builder = PositionBuilder(
        instrument_id=aapl_stock.id,
        native_currency="USD",
        reporting_currency="CZK",
    )
    rates = FxRates(date(2026, 1, 1), "USD", {"CZK": Decimal("20.0")})

    # 1. Try selling when having 0 holdings
    tx_sell = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        asset_account_id=sample_asset_account.id,
        instrument_id=aapl_stock.id,
        type=TransactionType.SELL,
        quantity=Decimal("5"),
        price=Money(Decimal("180"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("900"), "USD"),
    )
    with pytest.raises(ValueError, match="Short selling protection"):
        builder.add(tx_sell, rates)

    # 2. Buy 5, try to sell 6 (use a fresh builder since the previous failed add mutated self._last_trade_at)
    builder2 = PositionBuilder(
        instrument_id=aapl_stock.id,
        native_currency="USD",
        reporting_currency="CZK",
    )
    tx_buy = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        asset_account_id=sample_asset_account.id,
        instrument_id=aapl_stock.id,
        type=TransactionType.BUY,
        quantity=Decimal("5"),
        price=Money(Decimal("180"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("-900"), "USD"),
    )
    builder2.add(tx_buy, rates)

    tx_sell_excess = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
        asset_account_id=sample_asset_account.id,
        instrument_id=aapl_stock.id,
        type=TransactionType.SELL,
        quantity=Decimal("6"),
        price=Money(Decimal("180"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("1080"), "USD"),
    )
    with pytest.raises(ValueError, match="Short selling protection"):
        builder2.add(tx_sell_excess, rates)


def test_position_builder_closure_and_reopening(
    aapl_stock: Stock, sample_asset_account: AssetAccount
) -> None:
    builder = PositionBuilder(
        instrument_id=aapl_stock.id,
        native_currency="USD",
        reporting_currency="CZK",
    )
    rates = FxRates(date(2026, 1, 1), "USD", {"CZK": Decimal("20.0")})

    # Buy 5
    tx_buy = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        asset_account_id=sample_asset_account.id,
        instrument_id=aapl_stock.id,
        type=TransactionType.BUY,
        quantity=Decimal("5"),
        price=Money(Decimal("100"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("-500"), "USD"),
    )
    builder.add(tx_buy, rates)

    # Sell 5 (Fully closes)
    tx_sell = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
        asset_account_id=sample_asset_account.id,
        instrument_id=aapl_stock.id,
        type=TransactionType.SELL,
        quantity=Decimal("5"),
        price=Money(Decimal("120"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("600"), "USD"),
    )
    builder.add(tx_sell, rates)

    snapshot = builder.get_position_snapshot()
    assert snapshot.quantity == Decimal("0")
    assert snapshot.closed_at == datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)

    # Buy 10 (Reopens)
    tx_buy2 = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        asset_account_id=sample_asset_account.id,
        instrument_id=aapl_stock.id,
        type=TransactionType.BUY,
        quantity=Decimal("10"),
        price=Money(Decimal("110"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("-1100"), "USD"),
    )
    builder.add(tx_buy2, rates)

    snapshot2 = builder.get_position_snapshot()
    assert snapshot2.quantity == Decimal("10")
    assert snapshot2.closed_at is None
    assert snapshot2.cost_basis == DualMoney(
        Money(Decimal("1100"), "USD"), Money(Decimal("22000"), "CZK")
    )


def test_position_builder_unsupported_tx_type_raises_error(
    aapl_stock: Stock, sample_asset_account: AssetAccount
) -> None:
    builder = PositionBuilder(
        instrument_id=aapl_stock.id,
        native_currency="USD",
        reporting_currency="CZK",
    )
    rates = FxRates(date(2026, 1, 1), "USD", {"CZK": Decimal("20.0")})

    tx = Transaction(
        correlation_id=None,
        executed_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        asset_account_id=sample_asset_account.id,
        instrument_id=aapl_stock.id,
        type=TransactionType.DEPOSIT,  # DEPOSIT is not BUY/SELL
        quantity=Decimal("0"),
        price=Money(Decimal("0"), "USD"),
        fee=Money(Decimal("0"), "USD"),
        tax=Money(Decimal("0"), "USD"),
        cash_impact=Money(Decimal("100"), "USD"),
    )
    with pytest.raises(ValueError, match="Invalid transaction type"):
        builder.add(tx, rates)
