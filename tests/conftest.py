# pylint: disable=redefined-outer-name

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.institution import Institution
from portfolio_tracker.domain.instrument import Stock
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.shared import Money
from portfolio_tracker.domain.transaction import Transaction, TransactionType
from portfolio_tracker.domain.user import User

from .mocks import HyperactiveBrokersCredentials, Trading321Credentials



@pytest.fixture(scope="session")
def sample_institution_registry() -> InstitutionRegistry:
    return InstitutionRegistry(
        institutions={
            "inst_001": Institution(
                id="inst_001",
                name="Trading 321",
                log_in_url="https:\\trading321.com",
                credentials_cls=Trading321Credentials,
            ),
            "inst_002": Institution(
                id="inst_002",
                name="Hyperactive Brokers",
                log_in_url="https:\\hbkr.com",
                credentials_cls=HyperactiveBrokersCredentials,
            ),
        }
    )


@pytest.fixture(scope="session")
def sample_user() -> User:
    return User(
        id="usr_001",
        username="john_doe",
        password_hash="hash_abc123",
    )


@pytest.fixture(scope="session")
def sample_user_2() -> User:
    return User(
        id="usr_002",
        username="jane_doe",
        password_hash="hash_xyz789",
    )


@pytest.fixture(scope="session")
def sample_institution_account() -> InstitutionAccount:
    return InstitutionAccount(
        id="inst_acc_001",
        user_id="usr_001",
        institution_id="inst_001",
        name="Trading 321 Account",
        created_on=date(2026, 1, 1),
        last_synced_at=datetime(2026, 6, 1, 12, 0, 0),
    )


@pytest.fixture(scope="session")
def sample_asset_account() -> AssetAccount:
    return AssetAccount(
        id="ast_acc_001",
        institution_account_id="inst_acc_001",
        external_id="3210123",
        name="Invest",
    )


@pytest.fixture(scope="session")
def googl_stock() -> Stock:
    return Stock(
        name="Alphabet Inc.",
        symbol="GOOGL",
        exchange="NASDAQ",
        currency="USD",
        isin="US02079K3059",
        _id=None,
        _checksum=None,
    )


@pytest.fixture(scope="session")
def msft_stock() -> Stock:
    return Stock(
        name="Microsoft Corporation",
        symbol="MSFT",
        exchange="NASDAQ",
        currency="USD",
        isin="US5949181045",
        _id=None,
        _checksum=None,
    )


@pytest.fixture(scope="session")
def aapl_stock() -> Stock:
    return Stock(
        name="Apple Inc.",
        symbol="AAPL",
        exchange="NASDAQ",
        currency="USD",
        isin="US0378331005",
        _id=None,
        _checksum=None,
    )


@pytest.fixture(scope="session")
def nvda_stock() -> Stock:
    return Stock(
        name="NVIDIA Corporation",
        symbol="NVDA",
        exchange="NASDAQ",
        currency="USD",
        isin="US67066G1040",
        _id=None,
        _checksum=None,
    )


@pytest.fixture(scope="session")
def sample_buy_transaction() -> Transaction:
    return Transaction(
        executed_at=datetime(2026, 6, 1, 9, 15, 0, tzinfo=timezone.utc),
        asset_account_id="ast_acc_001",
        type=TransactionType.BUY,
        instrument_id="instr_001",
        quantity=Decimal("10"),
        price=Money(Decimal("100.50"), "USD"),
        fee=Money(Decimal("5"), "USD"),
        tax=Money.zero("USD"),
        cash_impact=Money(Decimal("-1010.00"), "USD"),
    )


@pytest.fixture(scope="session")
def sample_rates() -> FxRates:
    return FxRates(
        effective_on=date(2026, 6, 1),
        base_currency="USD",
        base_rates={
            "EUR": Decimal("0.90"),
            "CZK": Decimal("23.00"),
        },
    )


@pytest.fixture(scope="session")
def sample_stock_splits(aapl_stock: Stock) -> StockSplits:
    return StockSplits(
        instrument_id=aapl_stock.id,
        splits={
            datetime(2026, 6, 15, 0, 0, 0, tzinfo=timezone.utc): Decimal("2.0"),
            datetime(2026, 6, 18, 0, 0, 0, tzinfo=timezone.utc): Decimal("3.0"),
        },
    )
