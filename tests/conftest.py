# pylint: disable=redefined-outer-name

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.domain.account import AssetAccount
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.institution import (
    Credentials,
    Institution,
    InstitutionConnection,
)
from portfolio_tracker.domain.instrument import Stock
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.shared import Currency, Money
from portfolio_tracker.domain.transaction import Transaction, TransactionType
from portfolio_tracker.domain.user import User

from .mocks import (
    HyperactiveBrokersCredentials,
    MockInstitutionCode,
    Trading321Credentials,
)


@pytest.fixture(scope="session")
def sample_institution_registry() -> InstitutionRegistry:
    return InstitutionRegistry(
        institution_id_cls=MockInstitutionCode,
        institution_map={
            MockInstitutionCode.TRADING_321: Institution(
                id=MockInstitutionCode.TRADING_321,
                name="Trading 321",
                log_in_url="https:\\trading321.com",
            ),
            MockInstitutionCode.HYPERACTIVE_BROKERS: Institution(
                id=MockInstitutionCode.HYPERACTIVE_BROKERS,
                name="Hyperactive Brokers",
                log_in_url="https:\\hbkr.com",
            ),
        },
        credentials_map={
            MockInstitutionCode.TRADING_321: Trading321Credentials,
            MockInstitutionCode.HYPERACTIVE_BROKERS: HyperactiveBrokersCredentials,
        },
        client_map={},
        parser_map={},
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
def sample_institution_connection() -> InstitutionConnection:
    return InstitutionConnection(
        id="conn_001",
        user_id="usr_001",
        institution_id=MockInstitutionCode.TRADING_321,
        name="Trading 321 Account",
        sync_from=date(2026, 1, 1),
        last_synced_at=datetime(2026, 6, 1, 12, 0, 0),
    )


@pytest.fixture(scope="session")
def sample_credentials(
    sample_institution_registry: InstitutionRegistry,
    sample_institution_connection: InstitutionConnection,
) -> Credentials:
    return sample_institution_registry.create_credentials(
        institution_id=sample_institution_connection.institution_id,
        institution_connection_id=sample_institution_connection.id,
        parameters={
            "account_id": "0123456",
            "api_key": "key_123",
            "api_secret": "secret_abc",
        },
    )


@pytest.fixture(scope="session")
def sample_account() -> AssetAccount:
    return AssetAccount(
        id="acc_001",
        institution_connection_id="conn_001",
        external_id="3210123",
        name="Invest",
    )


@pytest.fixture(scope="session")
def sample_transaction(googl_stock: Stock) -> Transaction:
    return Transaction(
        executed_at=datetime(2026, 6, 1, 16, 15, 0, tzinfo=timezone.utc),
        account_id="acc_001",
        type=TransactionType.BUY,
        instrument_id=googl_stock.id,
        quantity=Decimal("10"),
        price=Money(Decimal("100.50"), Currency.USD),
        fee=Money.zero(Currency.USD),
        tax=Money.zero(Currency.USD),
        cash_impact=Money(Decimal("-1005.00"), Currency.USD),
    )


@pytest.fixture(scope="session")
def sample_stock(googl_stock: Stock) -> Stock:
    return googl_stock


@pytest.fixture(scope="session")
def googl_stock() -> Stock:
    return Stock(
        name="Alphabet Inc.",
        symbol="GOOGL",
        exchange="NASDAQ",
        currency=Currency.USD,
        isin="US02079K3059",
    )


@pytest.fixture(scope="session")
def msft_stock() -> Stock:
    return Stock(
        name="Microsoft Corporation",
        symbol="MSFT",
        exchange="NASDAQ",
        currency=Currency.USD,
        isin="US5949181045",
    )


@pytest.fixture(scope="session")
def aapl_stock() -> Stock:
    return Stock(
        name="Apple Inc.",
        symbol="AAPL",
        exchange="NASDAQ",
        currency=Currency.USD,
        isin="US0378331005",
    )


@pytest.fixture(scope="session")
def nvda_stock() -> Stock:
    return Stock(
        name="NVIDIA Corporation",
        symbol="NVDA",
        exchange="NASDAQ",
        currency=Currency.USD,
        isin="US67066G1040",
    )


@pytest.fixture(scope="session")
def sample_rates() -> FxRates:
    return FxRates(
        effective_on=date(2026, 6, 1),
        base_currency=Currency.USD,
        rates={
            Currency.EUR: Decimal("0.90"),
            Currency.CZK: Decimal("23.00"),
        },
    )


@pytest.fixture(scope="session")
def sample_stock_splits(googl_stock: Stock) -> StockSplits:
    return StockSplits(
        instrument_id=googl_stock.id,
        splits={
            datetime(2014, 3, 27, 0, 0, 0, tzinfo=timezone.utc): Decimal("2.0"),
            datetime(2022, 7, 18, 0, 0, 0, tzinfo=timezone.utc): Decimal("20.0"),
        },
    )
