# pylint: disable=redefined-outer-name

import sqlite3
from dataclasses import replace

import pytest

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.domain.account import AssetAccount
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.institution import Credentials, InstitutionConnection
from portfolio_tracker.domain.instrument import Stock
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.transaction import Transaction
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


@pytest.fixture
def user_repository(
    initialized_memory_db_connection: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
) -> SqliteUserRepository:
    return SqliteUserRepository(
        SqliteExecutor(
            connection=initialized_memory_db_connection,
            builder=statement_builder,
        )
    )


@pytest.fixture
def institution_connection_repository(
    initialized_memory_db_connection: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
    sample_institution_registry: InstitutionRegistry,
    sample_user: User,
) -> SqliteInstitutionConnectionRepository:
    return SqliteInstitutionConnectionRepository(
        user_id=sample_user.id,
        executor=SqliteExecutor(
            connection=initialized_memory_db_connection,
            builder=statement_builder,
        ),
        institution_registry=sample_institution_registry,
    )


@pytest.fixture
def credentials_repository(
    initialized_memory_db_connection: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
    sample_institution_registry: InstitutionRegistry,
    mock_encryptor: MockEncryptor,
    sample_user: User,
) -> SqliteCredentialsRepository:
    return SqliteCredentialsRepository(
        user_id=sample_user.id,
        executor=SqliteExecutor(
            connection=initialized_memory_db_connection,
            builder=statement_builder,
        ),
        institution_registry=sample_institution_registry,
        encryptor=mock_encryptor,
    )


@pytest.fixture
def account_repository(
    initialized_memory_db_connection: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
    sample_user: User,
) -> SqliteAccountRepository:
    return SqliteAccountRepository(
        user_id=sample_user.id,
        executor=SqliteExecutor(
            connection=initialized_memory_db_connection,
            builder=statement_builder,
        ),
    )


@pytest.fixture
def transaction_repository(
    initialized_memory_db_connection: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
    sample_user: User,
) -> SqliteTransactionRepository:
    return SqliteTransactionRepository(
        user_id=sample_user.id,
        executor=SqliteExecutor(
            connection=initialized_memory_db_connection,
            builder=statement_builder,
        ),
    )


@pytest.fixture
def instrument_repository(
    initialized_memory_db_connection: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
) -> SqliteInstrumentRepository:
    return SqliteInstrumentRepository(
        executor=SqliteExecutor(
            connection=initialized_memory_db_connection,
            builder=statement_builder,
        ),
    )


@pytest.fixture
def fx_rates_repository(
    initialized_memory_db_connection: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
) -> SqliteFxRatesRepository:
    return SqliteFxRatesRepository(
        executor=SqliteExecutor(
            connection=initialized_memory_db_connection,
            builder=statement_builder,
        ),
    )


@pytest.fixture
def market_data_repository(
    initialized_memory_db_connection: sqlite3.Connection,
    statement_builder: SqliteStatementBuilder,
) -> SqliteMarketDataRepository:
    return SqliteMarketDataRepository(
        executor=SqliteExecutor(
            connection=initialized_memory_db_connection,
            builder=statement_builder,
        ),
    )


@pytest.fixture
def stored_user(user_repository: SqliteUserRepository, sample_user: User) -> User:
    user_repository.add(sample_user)
    return sample_user


@pytest.fixture
def stored_institution_connection(
    stored_user: User,  # pylint: disable=unused-argument
    institution_connection_repository: SqliteInstitutionConnectionRepository,
    sample_institution_connection: InstitutionConnection,
) -> InstitutionConnection:
    institution_connection_repository.add(sample_institution_connection)
    return sample_institution_connection


@pytest.fixture
def stored_credentials(
    stored_institution_connection: InstitutionConnection,  # pylint: disable=unused-argument
    credentials_repository: SqliteCredentialsRepository,
    sample_credentials: Credentials,
) -> Credentials:
    credentials_repository.upsert(sample_credentials)
    return sample_credentials


@pytest.fixture
def stored_account(
    stored_institution_connection: InstitutionConnection,  # pylint: disable=unused-argument
    account_repository: SqliteAccountRepository,
    sample_account: AssetAccount,
) -> AssetAccount:
    account_repository.ensure(sample_account)
    return sample_account


@pytest.fixture
def stored_transaction(
    stored_account: AssetAccount,  # pylint: disable=unused-argument
    stored_stock: Stock,  # pylint: disable=unused-argument
    transaction_repository: SqliteTransactionRepository,
    sample_transaction: Transaction,
) -> Transaction:
    transaction_repository.ensure(sample_transaction)
    return sample_transaction


@pytest.fixture
def stored_stock(
    instrument_repository: SqliteInstrumentRepository,
    sample_stock: Stock,
) -> Stock:
    instrument_repository.ensure(sample_stock)
    return sample_stock


@pytest.fixture
def stored_rates(
    fx_rates_repository: SqliteFxRatesRepository,
    sample_rates: FxRates,
) -> FxRates:
    fx_rates_repository.ensure(sample_rates)
    return sample_rates


@pytest.fixture
def stored_stock_splits(
    stored_stock: Stock,  # pylint: disable=unused-argument
    market_data_repository: SqliteMarketDataRepository,
    sample_stock_splits: StockSplits,
) -> StockSplits:
    market_data_repository.ensure_stock_splits(sample_stock_splits)
    return sample_stock_splits


def test_user_repository_round_trips_user(
    user_repository: SqliteUserRepository,
    stored_user: User,
) -> None:
    loaded_user = user_repository.get_by_username(stored_user.username)
    assert loaded_user == stored_user


def test_institution_connection_repository_round_trips_institution_connection(
    institution_connection_repository: SqliteInstitutionConnectionRepository,
    stored_institution_connection: InstitutionConnection,
) -> None:
    loaded_institution_connection = institution_connection_repository.get_by_id(
        stored_institution_connection.id
    )
    assert loaded_institution_connection == stored_institution_connection


def test_credentials_repository_round_trips_credentials(
    credentials_repository: SqliteCredentialsRepository,
    stored_credentials: Credentials,
) -> None:
    loaded_credentials = credentials_repository.get(
        stored_credentials.institution_connection_id
    )
    assert loaded_credentials == stored_credentials


def test_credentials_repository_removes_credentials_for_owned_connection(
    credentials_repository: SqliteCredentialsRepository,
    stored_credentials: Credentials,
) -> None:
    assert (
        credentials_repository.remove(stored_credentials.institution_connection_id) == 1
    )
    assert (
        credentials_repository.get(stored_credentials.institution_connection_id) is None
    )


def test_account_repository_round_trips_account(
    account_repository: SqliteAccountRepository,
    stored_account: AssetAccount,
) -> None:
    loaded_account = account_repository.get_by_id(stored_account.id)
    loaded_account_2 = account_repository.get_by_external_id(
        stored_account.institution_connection_id, stored_account.external_id
    )
    loaded_accounts = account_repository.get_by_institution_connection_id(
        stored_account.institution_connection_id
    )
    assert loaded_account == stored_account
    assert loaded_account_2 == stored_account
    assert len(loaded_accounts) == 1
    assert loaded_accounts[0] == stored_account


def test_account_repository_update_is_scoped_to_user(
    account_repository: SqliteAccountRepository,
    stored_account: AssetAccount,
) -> None:
    updated_account = replace(stored_account, name="Updated")

    assert account_repository.update(updated_account) == 1
    assert account_repository.get_by_id(stored_account.id) == updated_account


def test_transaction_repository_round_trips_transaction(
    transaction_repository: SqliteTransactionRepository,
    stored_transaction: Transaction,
) -> None:
    loaded_transaction = transaction_repository.get_by_id(stored_transaction.id)
    assert loaded_transaction == stored_transaction


def test_instrument_repository_round_trips_stock_instrument(
    instrument_repository: SqliteInstrumentRepository,
    stored_stock: Stock,
) -> None:
    loaded_instruments = instrument_repository.get()
    assert len(loaded_instruments) == 1
    assert loaded_instruments[0] == stored_stock


def test_fx_rates_repository_round_trips_fx_rates(
    fx_rates_repository: SqliteFxRatesRepository,
    stored_rates: FxRates,
) -> None:
    loaded_rates = fx_rates_repository.get_by_date(stored_rates.effective_on)
    assert loaded_rates == stored_rates


def test_market_data_repository_round_trips_stock_splits(
    market_data_repository: SqliteMarketDataRepository,
    stored_stock_splits: StockSplits,
) -> None:
    loaded_stock_splits_list = (
        market_data_repository.get_stock_splits_by_instrument_ids(
            {stored_stock_splits.instrument_id}
        )
    )
    assert len(loaded_stock_splits_list) == 1
    assert loaded_stock_splits_list[0] == stored_stock_splits
