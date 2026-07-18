# pylint: disable=protected-access
# pylint: disable=redefined-outer-name

import sqlite3

import pytest

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.domain.user import User
from portfolio_tracker.infrastructure.persistence.sqlite import SqliteUnitOfWork
from tests.mocks import MockEncryptor


@pytest.fixture
def shared_memory_uow(
    initialized_shared_memory_db_uri: str,
    mock_encryptor: MockEncryptor,
    sample_institution_registry: InstitutionRegistry,
) -> SqliteUnitOfWork:
    return SqliteUnitOfWork(
        initialized_shared_memory_db_uri,
        mock_encryptor,
        sample_institution_registry,
        uri=True,
    )


def test_unit_of_work_transaction_lifecycle(
    shared_memory_uow: SqliteUnitOfWork,
) -> None:
    connection = shared_memory_uow._connection
    assert connection is None

    with shared_memory_uow:
        assert shared_memory_uow._connection is not None
        assert shared_memory_uow._connection.in_transaction is True

        shared_memory_uow._connection.execute("""
            CREATE TABLE test (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                passed INTEGER,
                failed INTEGER
            );
            """)
        shared_memory_uow.commit()

        assert shared_memory_uow._connection.in_transaction is False

    assert shared_memory_uow._connection is None


def test_rollback_occurs_when_transaction_aborts(
    shared_memory_uow: SqliteUnitOfWork,
    sample_user: User,
    sample_user_2: User,
) -> None:
    with shared_memory_uow:
        shared_memory_uow.users.add(sample_user)
        shared_memory_uow.commit()

    with pytest.raises(RuntimeError, match="Mock database operation fail."):
        with shared_memory_uow:
            shared_memory_uow.users.add(sample_user_2)
            raise RuntimeError("Mock database operation fail.")

    with shared_memory_uow:
        assert (
            shared_memory_uow.users.get_by_username(sample_user.username) == sample_user
        )
        assert shared_memory_uow.users.get_by_username(sample_user_2.username) is None


def test_explicit_commit_needed_to_write_database_changes(
    shared_memory_uow: SqliteUnitOfWork,
    sample_user: User,
) -> None:
    with shared_memory_uow:
        shared_memory_uow.users.add(sample_user)
        # uow.commit()

    with shared_memory_uow:
        assert shared_memory_uow.users.get_by_username(sample_user.username) is None


def test_write_connection_does_not_block_read_connection(
    initialized_tmp_db_path: str,
    mock_encryptor: MockEncryptor,
    sample_institution_registry: InstitutionRegistry,
    sample_user: User,
) -> None:
    uow_1 = SqliteUnitOfWork(
        initialized_tmp_db_path,
        mock_encryptor,
        sample_institution_registry,
    )
    uow_2 = SqliteUnitOfWork(
        initialized_tmp_db_path,
        mock_encryptor,
        sample_institution_registry,
        read_only=True,
    )

    with uow_1:
        uow_1.users.add(sample_user)

        with uow_2:
            user = uow_2.users.get_by_username(sample_user.username)
            assert user is None

        uow_1.commit()

    with uow_2:
        user = uow_2.users.get_by_username(sample_user.username)
        assert user is not None
        assert user == sample_user


def test_two_connections_cannot_write_at_the_same_time(
    initialized_tmp_db_path: str,
    mock_encryptor: MockEncryptor,
    sample_institution_registry: InstitutionRegistry,
    sample_user: User,
    sample_user_2: User,
) -> None:
    uow_1 = SqliteUnitOfWork(
        initialized_tmp_db_path,
        mock_encryptor,
        sample_institution_registry,
    )
    uow_2 = SqliteUnitOfWork(
        initialized_tmp_db_path,
        mock_encryptor,
        sample_institution_registry,
        timeout=0,
    )

    with uow_1:
        uow_1.users.add(sample_user)

        with pytest.raises(sqlite3.OperationalError, match="database is locked"):
            with uow_2:
                uow_2.users.add(sample_user_2)
