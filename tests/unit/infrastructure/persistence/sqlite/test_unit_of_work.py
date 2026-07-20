# pylint: disable=protected-access
# pylint: disable=redefined-outer-name

import sqlite3
from typing import Callable

import pytest

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.domain.user import User
from portfolio_tracker.infrastructure.persistence.sqlite import SqliteUnitOfWork
from tests.mocks import MockEncryptor


@pytest.fixture
def shared_memory_uow(
    initialized_shared_memory_db_connection: sqlite3.Connection,
    mock_encryptor: MockEncryptor,
    sample_institution_registry: InstitutionRegistry,
) -> SqliteUnitOfWork:
    return SqliteUnitOfWork(
        initialized_shared_memory_db_connection,
        mock_encryptor,
        sample_institution_registry,
    )


def test_unit_of_work_transaction_lifecycle(
    shared_memory_uow: SqliteUnitOfWork,
) -> None:
    connection = shared_memory_uow._connection
    assert connection is not None

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

    assert shared_memory_uow._connection is not None


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
        # uow.commit() omitted

    with shared_memory_uow:
        assert shared_memory_uow.users.get_by_username(sample_user.username) is None


def test_write_connection_does_not_block_read_connection(
    open_initialized_tmp_db_connection: Callable[..., sqlite3.Connection],
    mock_encryptor: MockEncryptor,
    sample_institution_registry: InstitutionRegistry,
    sample_user: User,
) -> None:
    connection_1 = open_initialized_tmp_db_connection()
    uow_1 = SqliteUnitOfWork(
        connection_1,
        mock_encryptor,
        sample_institution_registry,
    )

    connection_2 = open_initialized_tmp_db_connection()
    uow_2 = SqliteUnitOfWork(
        connection_2,
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
    open_initialized_tmp_db_connection: Callable[..., sqlite3.Connection],
    mock_encryptor: MockEncryptor,
    sample_institution_registry: InstitutionRegistry,
    sample_user: User,
    sample_user_2: User,
) -> None:
    connection_1 = open_initialized_tmp_db_connection()
    uow_1 = SqliteUnitOfWork(
        connection_1,
        mock_encryptor,
        sample_institution_registry,
    )

    connection_2 = open_initialized_tmp_db_connection(timeout=0)
    uow_2 = SqliteUnitOfWork(
        connection_2,
        mock_encryptor,
        sample_institution_registry,
    )

    with uow_1:
        uow_1.users.add(sample_user)

        with pytest.raises(sqlite3.OperationalError, match="database is locked"):
            with uow_2:
                uow_2.users.add(sample_user_2)
