# pylint: disable=protected-access
# pylint: disable=redefined-outer-name

import sqlite3
from typing import Callable, Protocol

import pytest

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.domain.user import User
from portfolio_tracker.infrastructure.persistence.sqlite.builder import (
    SqliteStatementBuilder,
)
from portfolio_tracker.infrastructure.persistence.sqlite.database import open_connection
from portfolio_tracker.infrastructure.persistence.sqlite.executor import SqliteExecutor
from portfolio_tracker.infrastructure.persistence.sqlite.unit_of_work import (
    SqliteUnitOfWork,
)
from tests.mocks import MockEncryptor


class UnitOfWorkFactory(Protocol):
    def __call__(
        self, connection: sqlite3.Connection, *, read_only: bool = False
    ) -> SqliteUnitOfWork: ...


@pytest.fixture(scope="module")
def create_uow(
    sample_institution_registry: InstitutionRegistry,
    mock_encryptor: MockEncryptor,
    statement_builder: SqliteStatementBuilder,
) -> UnitOfWorkFactory:
    def create(
        connection: sqlite3.Connection, *, read_only: bool = False
    ) -> SqliteUnitOfWork:
        return SqliteUnitOfWork(
            user_id=None,
            institution_registry=sample_institution_registry,
            encryptor=mock_encryptor,
            executor=SqliteExecutor(connection, statement_builder),
            read_only=read_only,
        )

    return create


@pytest.fixture(scope="module")
def create_test_table_sql() -> str:
    return """
        CREATE TABLE test (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            passed INTEGER,
            failed INTEGER
        );
    """


@pytest.fixture
def initialized_in_memory_uow(
    create_uow: UnitOfWorkFactory,
    initialized_memory_db_connection: sqlite3.Connection,
) -> SqliteUnitOfWork:
    return create_uow(initialized_memory_db_connection)


def test_unit_of_work_transaction_lifecycle(
    initialized_in_memory_uow: SqliteUnitOfWork,
    create_test_table_sql: str,
) -> None:
    def test_if_transaction_is_active(expected_is_active: bool) -> None:
        assert (
            initialized_in_memory_uow._executor._connection.in_transaction
            is expected_is_active
        )
        assert initialized_in_memory_uow._is_active is expected_is_active

    test_if_transaction_is_active(expected_is_active=False)

    with initialized_in_memory_uow:
        test_if_transaction_is_active(expected_is_active=True)

        initialized_in_memory_uow._executor.execute(create_test_table_sql)
        initialized_in_memory_uow.commit()

        test_if_transaction_is_active(expected_is_active=False)

    test_if_transaction_is_active(expected_is_active=False)


def test_rollback_occurs_when_transaction_aborts(
    initialized_in_memory_uow: SqliteUnitOfWork,
    sample_user: User,
    sample_user_2: User,
) -> None:
    with initialized_in_memory_uow:
        initialized_in_memory_uow.users.add(sample_user)
        initialized_in_memory_uow.commit()

    with pytest.raises(RuntimeError, match="Mock error."):
        with initialized_in_memory_uow:
            initialized_in_memory_uow.users.add(sample_user_2)
            raise RuntimeError("Mock error.")

    with initialized_in_memory_uow:
        assert (
            initialized_in_memory_uow.users.get_by_username(sample_user.username)
            == sample_user
        )
        assert (
            initialized_in_memory_uow.users.get_by_username(sample_user_2.username)
            is None
        )


def test_explicit_commit_needed_to_write_database_changes(
    initialized_in_memory_uow: SqliteUnitOfWork,
    sample_user: User,
) -> None:
    with initialized_in_memory_uow:
        initialized_in_memory_uow.users.add(sample_user)
        # uow.commit() intentionally omitted

    with initialized_in_memory_uow:
        assert (
            initialized_in_memory_uow.users.get_by_username(sample_user.username)
            is None
        )


def test_read_only_unit_of_work_rejects_writes(
    memory_db_uri: str,
    create_uow: UnitOfWorkFactory,
    create_test_table_sql: str,
) -> None:
    connection = open_connection(memory_db_uri, read_only=True)
    read_uow = create_uow(connection, read_only=True)

    with read_uow:
        with pytest.raises(
            sqlite3.OperationalError, match="readonly database|read-only"
        ):
            read_uow._executor.execute(create_test_table_sql)

        cursor = read_uow._executor.execute("""
            SELECT name 
            FROM sqlite_schema 
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%';
        """)
        tables = [row[0] for row in cursor.fetchall()]
        assert len(tables) == 0


def test_write_connection_does_not_block_read_connection(
    create_uow: UnitOfWorkFactory,
    open_initialized_temp_db_connection: Callable[..., sqlite3.Connection],
    sample_user: User,
) -> None:
    write_connection = open_initialized_temp_db_connection()
    write_uow = create_uow(write_connection)

    read_connection = open_initialized_temp_db_connection(read_only=True)
    read_uow = create_uow(read_connection, read_only=True)

    with write_uow:
        write_uow.users.add(sample_user)

        with read_uow:
            user = read_uow.users.get_by_username(sample_user.username)
            assert user is None

        write_uow.commit()

    with read_uow:
        user = read_uow.users.get_by_username(sample_user.username)
        assert user is not None
        assert user == sample_user


def test_two_connections_cannot_write_at_the_same_time(
    create_uow: UnitOfWorkFactory,
    open_initialized_temp_db_connection: Callable[..., sqlite3.Connection],
    sample_user: User,
    sample_user_2: User,
) -> None:
    write_connection_1 = open_initialized_temp_db_connection()
    write_uow_1 = create_uow(write_connection_1)

    write_connection_2 = open_initialized_temp_db_connection(timeout=0)
    write_uow_2 = create_uow(write_connection_2)

    with write_uow_1:
        write_uow_1.users.add(sample_user)

        with pytest.raises(sqlite3.OperationalError, match="database is locked"):
            with write_uow_2:
                write_uow_2.users.add(sample_user_2)
