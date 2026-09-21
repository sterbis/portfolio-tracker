import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.domain.account import AssetAccount
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.institution import InstitutionConnection
from portfolio_tracker.domain.instrument import Stock
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.shared import Currency, Money
from portfolio_tracker.domain.transaction import Transaction, TransactionType
from portfolio_tracker.domain.user import User
from portfolio_tracker.infrastructure.persistence.sqlite.builder import (
    SqliteStatementBuilder,
)
from portfolio_tracker.infrastructure.persistence.sqlite.executor import SqliteExecutor
from portfolio_tracker.infrastructure.persistence.sqlite.repositories import (
    SqliteAccountRepository,
    SqliteCredentialsRepository,
    SqliteFxRatesRepository,
    SqliteInstitutionConnectionRepository,
    SqliteInstrumentRepository,
    SqliteMarketDataRepository,
    SqliteTransactionRepository,
    SqliteUserRepository,
)
from tests.mocks import MockEncryptor


def test_user_repository_round_trips_user(
    initialized_in_memory_db_connection: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
    sample_user: User,
) -> None:
    repository = SqliteUserRepository(
        SqliteExecutor(
            connection=initialized_in_memory_db_connection,
            builder=statement_builder,
        )
    )
    repository.add(sample_user)
    stored_user = repository.get_by_username(sample_user.username)
    assert stored_user == sample_user


def test_institution_connection_repository_round_trips_institution_connection(
    initialized_in_memory_db_connection_foreign_keys_off: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
    sample_institution_registry: InstitutionRegistry,
    sample_institution_connection: InstitutionConnection,
) -> None:
    repository = SqliteInstitutionConnectionRepository(
        institution_registry=sample_institution_registry,
        executor=SqliteExecutor(
            connection=initialized_in_memory_db_connection_foreign_keys_off,
            builder=statement_builder,
        ),
    )
    repository.add(sample_institution_connection)
    stored_institution_connection = repository.get_by_id(
        sample_institution_connection.id
    )
    assert stored_institution_connection == sample_institution_connection


def test_account_repository_round_trips_account(
    initialized_in_memory_db_connection_foreign_keys_off: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
    sample_account: AssetAccount,
) -> None:
    repository = SqliteAccountRepository(
        SqliteExecutor(
            connection=initialized_in_memory_db_connection_foreign_keys_off,
            builder=statement_builder,
        ),
    )
    repository.ensure(sample_account)
    stored_asset_account = repository.get_by_id(sample_account.id)
    stored_asset_account_2 = repository.get_by_external_id(
        sample_account.institution_connection_id, sample_account.external_id
    )
    stored_asset_accounts = repository.get_by_institution_connection_id(
        sample_account.institution_connection_id
    )

    assert stored_asset_account == sample_account
    assert stored_asset_account_2 == sample_account
    assert len(stored_asset_accounts) == 1
    assert stored_asset_accounts[0] == sample_account


def test_credentials_repository_round_trips_credentials(
    initialized_in_memory_db_connection_foreign_keys_off: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
    mock_encryptor: MockEncryptor,
    sample_institution_registry: InstitutionRegistry,
    sample_institution_connection: InstitutionConnection,
) -> None:
    parameters = {
        "api_key": "key_123",
        "api_secret": "secret_abc",
    }
    credentials = sample_institution_registry.create_credentials(
        sample_institution_connection.institution_id,
        sample_institution_connection.id,
        parameters,
    )

    credentials_repository = SqliteCredentialsRepository(
        institution_registry=sample_institution_registry,
        encryptor=mock_encryptor,
        executor=SqliteExecutor(
            connection=initialized_in_memory_db_connection_foreign_keys_off,
            builder=statement_builder,
        ),
    )
    credentials_repository.upsert(credentials)

    stored_credentials = credentials_repository.get(sample_institution_connection.id)
    assert stored_credentials == credentials


def test_transaction_repository_round_trips_transaction(
    initialized_in_memory_db_connection_foreign_keys_off: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
    sample_account: AssetAccount,
    googl_stock: Stock,
) -> None:
    transaction_repository = SqliteTransactionRepository(
        executor=SqliteExecutor(
            connection=initialized_in_memory_db_connection_foreign_keys_off,
            builder=statement_builder,
        ),
    )

    transaction = Transaction(
        executed_at=datetime(2026, 6, 1, 16, 15, 0, tzinfo=timezone.utc),
        account_id=sample_account.id,
        type=TransactionType.BUY,
        instrument_id=googl_stock.id,
        quantity=Decimal("10"),
        price=Money(Decimal("100.50"), Currency.USD),
        fee=Money.zero(Currency.USD),
        tax=Money.zero(Currency.USD),
        cash_impact=Money(Decimal("-1005.00"), Currency.USD),
    )
    transaction_repository.add(transaction)

    stored_transaction = transaction_repository.get_by_id(transaction.id)
    assert stored_transaction == transaction


def test_instrument_repository_round_trips_stock_instrument(
    initialized_in_memory_db_connection: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
    googl_stock: Stock,
) -> None:
    repository = SqliteInstrumentRepository(
        executor=SqliteExecutor(
            connection=initialized_in_memory_db_connection,
            builder=statement_builder,
        ),
    )
    repository.ensure(googl_stock)

    stored_instruments = repository.get()
    assert len(stored_instruments) == 1
    assert stored_instruments[0] == googl_stock


def test_fx_rates_repository_round_trips_fx_rates(
    initialized_in_memory_db_connection: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
    sample_rates: FxRates,
) -> None:
    repository = SqliteFxRatesRepository(
        executor=SqliteExecutor(
            connection=initialized_in_memory_db_connection,
            builder=statement_builder,
        ),
    )
    repository.ensure(sample_rates)
    stored_rates = repository.get_by_date(sample_rates.effective_on)
    assert stored_rates == sample_rates


def test_market_data_repository_round_trips_stock_splits(
    initialized_in_memory_db_connection_foreign_keys_off: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
    sample_stock_splits: StockSplits,
) -> None:
    repository = SqliteMarketDataRepository(
        executor=SqliteExecutor(
            connection=initialized_in_memory_db_connection_foreign_keys_off,
            builder=statement_builder,
        )
    )
    repository.ensure_stock_splits(sample_stock_splits)
    results = repository.get_stock_splits_by_instrument_ids(
        {sample_stock_splits.instrument_id}
    )
    assert len(results) == 1
    assert results[0] == sample_stock_splits
