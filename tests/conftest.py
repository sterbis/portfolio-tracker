import pytest

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from portfolio_tracker.domain.accounts import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.institution import (
    Credentials,
    Institution,
    InstitutionRegistry,
)
from portfolio_tracker.domain.instruments import Stock
from portfolio_tracker.domain.ledger import Transaction, TransactionType
from portfolio_tracker.domain.shared import Money
from portfolio_tracker.domain.user import User


@pytest.fixture(scope="session")
def sample_institution_registry() -> InstitutionRegistry:
    @dataclass(frozen=True)
    class Trading321Credentials(Credentials):
        api_key: str
        api_secret: str

    @dataclass(frozen=True)
    class HyperactiveBrokerCredentials(Credentials):
        web_service_token: str
        query_ids: list[str]

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
                credentials_cls=HyperactiveBrokerCredentials,
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
        _id=None,
        name="Alphabet Inc.",
        symbol="GOOGL",
        exchange="NASDAQ",
        currency="USD",
        isin="US02079K3059",
    )


@pytest.fixture(scope="session")
def msft_stock() -> Stock:
    return Stock(
        _id=None,
        name="Microsoft Corporation",
        symbol="MSFT",
        exchange="NASDAQ",
        currency="USD",
        isin="US5949181045",
    )


@pytest.fixture(scope="session")
def aapl_stock() -> Stock:
    return Stock(
        _id=None,
        name="Apple Inc.",
        symbol="AAPL",
        exchange="NASDAQ",
        currency="USD",
        isin="US0378331005",
    )


@pytest.fixture(scope="session")
def nvda_stock() -> Stock:
    return Stock(
        _id=None,
        name="NVIDIA Corporation",
        symbol="NVDA",
        exchange="NASDAQ",
        currency="USD",
        isin="US67066G1040",
    )


@pytest.fixture(scope="session")
def sample_buy_transaction() -> Transaction:
    return Transaction(
        correlation_id=None,
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
