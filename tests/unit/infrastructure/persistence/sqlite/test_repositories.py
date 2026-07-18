import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.instrument import Stock
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.shared import Money
from portfolio_tracker.domain.transaction import Transaction, TransactionType
from portfolio_tracker.domain.user import User
from portfolio_tracker.infrastructure.persistence.sqlite.executor import SqliteExecutor
from portfolio_tracker.infrastructure.persistence.sqlite.repositories import (
    SqliteAccountRepository,
    SqliteCredentialsRepository,
    SqliteFxRatesRepository,
    SqliteInstrumentRepository,
    SqliteMarketDataRepository,
    SqliteTransactionRepository,
    SqliteUserRepository,
)
from tests.mocks import MockEncryptor


def test_user_repository_round_trips_user(
    initialized_shared_memory_db_connection_foreign_keys_off: sqlite3.Connection,
    sample_user: User,
) -> None:
    repository = SqliteUserRepository(
        SqliteExecutor(initialized_shared_memory_db_connection_foreign_keys_off)
    )
    repository.add(sample_user)
    stored_user = repository.get_by_username(sample_user.username)
    assert stored_user == sample_user


def test_account_repository_round_trips_institution_and_asset_accounts(
    initialized_shared_memory_db_connection_foreign_keys_off: sqlite3.Connection,
    sample_institution_account: InstitutionAccount,
    sample_asset_account: AssetAccount,
) -> None:
    account_repository = SqliteAccountRepository(
        SqliteExecutor(initialized_shared_memory_db_connection_foreign_keys_off)
    )

    account_repository.add_institution_account(sample_institution_account)
    stored_institution_account = account_repository.get_institution_account_by_id(
        sample_institution_account.id
    )
    assert stored_institution_account == sample_institution_account

    account_repository.add_asset_account(sample_asset_account)
    stored_asset_account = account_repository.get_asset_account_by_external_id(
        sample_asset_account.institution_account_id, sample_asset_account.external_id
    )
    assert stored_asset_account == sample_asset_account


def test_credentials_repository_round_trips_credentials(
    initialized_shared_memory_db_connection: sqlite3.Connection,
    mock_encryptor: MockEncryptor,
    sample_institution_registry: InstitutionRegistry,
    sample_user: User,
    sample_institution_account: InstitutionAccount,
) -> None:
    institution = sample_institution_registry.get(
        sample_institution_account.institution_id
    )
    credentials_parameters = {
        "api_key": "key_123",
        "api_secret": "secret_abc",
    }
    credentials = institution.credentials_cls(**credentials_parameters)

    user_repository = SqliteUserRepository(
        SqliteExecutor(initialized_shared_memory_db_connection),
    )
    user_repository.add(sample_user)

    account_repository = SqliteAccountRepository(
        SqliteExecutor(initialized_shared_memory_db_connection),
    )
    account_repository.add_institution_account(sample_institution_account)

    credentials_repository = SqliteCredentialsRepository(
        sample_institution_registry,
        mock_encryptor,
        SqliteExecutor(initialized_shared_memory_db_connection),
    )
    credentials_repository.store(sample_institution_account.id, credentials)

    stored_credentials = credentials_repository.retrieve(sample_institution_account.id)
    assert stored_credentials == credentials


def test_transaction_repository_round_trips_transaction(
    initialized_shared_memory_db_connection_foreign_keys_off: sqlite3.Connection,
    sample_asset_account: AssetAccount,
    googl_stock: Stock,
) -> None:
    transaction_repository = SqliteTransactionRepository(
        SqliteExecutor(initialized_shared_memory_db_connection_foreign_keys_off)
    )

    transaction = Transaction(
        executed_at=datetime(2026, 6, 1, 16, 15, 0, tzinfo=timezone.utc),
        asset_account_id=sample_asset_account.id,
        type=TransactionType.BUY,
        instrument_id=googl_stock.id,
        quantity=Decimal("10"),
        price=Money(Decimal("100.50"), "USD"),
        fee=Money.zero("USD"),
        tax=Money.zero("USD"),
        cash_impact=Money(Decimal("-1005.00"), "USD"),
    )
    transaction_repository.add(transaction)

    stored_transaction = transaction_repository.get_by_id(transaction.id)
    assert stored_transaction == transaction


def test_instrument_repository_round_trips_stock_instrument(
    initialized_shared_memory_db_connection_foreign_keys_off: sqlite3.Connection,
    googl_stock: Stock,
) -> None:
    repository = SqliteInstrumentRepository(
        SqliteExecutor(initialized_shared_memory_db_connection_foreign_keys_off)
    )
    repository.ensure(googl_stock)

    stored_instruments = repository.get()
    assert len(stored_instruments) == 1
    assert stored_instruments[0] == googl_stock


def test_fx_rates_repository_round_trips_fx_rates(
    initialized_shared_memory_db_connection: sqlite3.Connection,
    sample_rates: FxRates,
) -> None:
    repository = SqliteFxRatesRepository(
        SqliteExecutor(initialized_shared_memory_db_connection)
    )
    repository.ensure(sample_rates)
    stored_rates = repository.get_by_date(sample_rates.effective_on)
    assert stored_rates == sample_rates


def test_market_data_repository_round_trips_stock_splits(
    initialized_shared_memory_db_connection_foreign_keys_off: sqlite3.Connection,
    sample_stock_splits: StockSplits,
) -> None:
    repository = SqliteMarketDataRepository(
        SqliteExecutor(initialized_shared_memory_db_connection_foreign_keys_off)
    )
    repository.ensure_stock_splits(sample_stock_splits)
    results = repository.get_stock_splits_by_instrument_ids(
        {sample_stock_splits.instrument_id}
    )
    assert len(results) == 1
    assert results[0] == sample_stock_splits
