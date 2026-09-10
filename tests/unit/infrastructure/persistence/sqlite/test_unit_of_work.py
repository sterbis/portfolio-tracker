# pylint: disable=protected-access
# pylint: disable=redefined-outer-name

import sqlite3
from typing import Callable, Protocol

import pytest

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.domain.user import User
from portfolio_tracker.infrastructure.persistence.sqlite import SqliteUnitOfWork
from portfolio_tracker.infrastructure.persistence.sqlite.builder import (
    SqliteStatementBuilder,
)
from tests.mocks import MockEncryptor


class UnitOfWorkFactory(Protocol):
    def __call__(
        self, connection: sqlite3.Connection, *, read_only: bool = False
    ) -> SqliteUnitOfWork: ...


@pytest.fixture(scope="module")
def create_unit_of_work(
    mock_encryptor: MockEncryptor,
    sample_institution_registry: InstitutionRegistry,
    statement_builder: SqliteStatementBuilder,
) -> UnitOfWorkFactory:
    def create(
        connection: sqlite3.Connection, *, read_only: bool = False
    ) -> SqliteUnitOfWork:
        return SqliteUnitOfWork(
            encryptor=mock_encryptor,
            institution_registry=sample_institution_registry,
            builder=statement_builder,
            connection=connection,
            read_only=read_only,
        )

    return create


@pytest.fixture
def in_memory_uow(
    create_unit_of_work: UnitOfWorkFactory,
    initialized_in_memory_db_connection: sqlite3.Connection,
) -> SqliteUnitOfWork:
    return create_unit_of_work(initialized_in_memory_db_connection)


def test_unit_of_work_transaction_lifecycle(
    in_memory_uow: SqliteUnitOfWork,
) -> None:
    def test_if_transaction_is_active(expected_is_active: bool) -> None:
        assert in_memory_uow._connection.in_transaction is expected_is_active
        assert in_memory_uow._is_active is expected_is_active

    test_if_transaction_is_active(expected_is_active=False)

    with in_memory_uow:
        test_if_transaction_is_active(expected_is_active=True)

        in_memory_uow._connection.execute("""
            CREATE TABLE test (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                passed INTEGER,
                failed INTEGER
            );
            """)
        in_memory_uow.commit()

        test_if_transaction_is_active(expected_is_active=False)

    test_if_transaction_is_active(expected_is_active=False)


def test_rollback_occurs_when_transaction_aborts(
    in_memory_uow: SqliteUnitOfWork,
    sample_user: User,
    sample_user_2: User,
) -> None:
    with in_memory_uow:
        in_memory_uow.users.add(sample_user)
        in_memory_uow.commit()

    with pytest.raises(RuntimeError, match="Mock database operation fail."):
        with in_memory_uow:
            in_memory_uow.users.add(sample_user_2)
            raise RuntimeError("Mock database operation fail.")

    with in_memory_uow:
        assert in_memory_uow.users.get_by_username(sample_user.username) == sample_user
        assert in_memory_uow.users.get_by_username(sample_user_2.username) is None


def test_explicit_commit_needed_to_write_database_changes(
    in_memory_uow: SqliteUnitOfWork,
    sample_user: User,
) -> None:
    with in_memory_uow:
        in_memory_uow.users.add(sample_user)
        # uow.commit() omitted

    with in_memory_uow:
        assert in_memory_uow.users.get_by_username(sample_user.username) is None


def test_write_connection_does_not_block_read_connection(
    create_unit_of_work: UnitOfWorkFactory,
    open_initialized_db_connection: Callable[..., sqlite3.Connection],
    sample_user: User,
) -> None:
    write_connection = open_initialized_db_connection()
    write_uow = create_unit_of_work(write_connection)

    read_connection = open_initialized_db_connection()
    read_uow = create_unit_of_work(read_connection, read_only=True)

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
    create_unit_of_work: UnitOfWorkFactory,
    open_initialized_db_connection: Callable[..., sqlite3.Connection],
    sample_user: User,
    sample_user_2: User,
) -> None:
    write_connection_1 = open_initialized_db_connection()
    write_uow_1 = create_unit_of_work(write_connection_1)

    write_connection_2 = open_initialized_db_connection(timeout=0)
    write_uow_2 = create_unit_of_work(write_connection_2)

    with write_uow_1:
        write_uow_1.users.add(sample_user)

        with pytest.raises(sqlite3.OperationalError, match="database is locked"):
            with write_uow_2:
                write_uow_2.users.add(sample_user_2)
