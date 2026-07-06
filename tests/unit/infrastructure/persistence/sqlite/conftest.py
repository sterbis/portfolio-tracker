# pylint: disable=redefined-outer-name

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from portfolio_tracker.infrastructure.persistence.sqlite import (
    initialize_database,
    open_connection,
    register_mappers,
)


@pytest.fixture(scope="session", autouse=True)
def register_sqlite_mappers() -> None:
    register_mappers()


@pytest.fixture(scope="session")
def schema_path() -> str:
    return r"src\portfolio_tracker\infrastructure\persistence\sqlite\schema.sql"


@pytest.fixture
def memory_db_connection() -> Iterator[sqlite3.Connection]:
    connection = open_connection(":memory:")
    yield connection
    connection.close()


@pytest.fixture
def shared_memory_db_uri() -> str:
    return "file:test_portfolio_db?mode=memory&cache=shared"


@pytest.fixture
def shared_memory_db_connection(
    shared_memory_db_uri: str,
) -> Iterator[sqlite3.Connection]:
    connection = open_connection(shared_memory_db_uri, uri=True)
    yield connection
    connection.close()


@pytest.fixture
def initialized_shared_memory_db_connection(
    shared_memory_db_uri: str,
    schema_path: str,
    shared_memory_db_connection: sqlite3.Connection,
) -> sqlite3.Connection:
    initialize_database(shared_memory_db_uri, schema_path, uri=True)
    return shared_memory_db_connection


@pytest.fixture
def shared_memory_db_connection_foreign_keys_off(
    shared_memory_db_connection: sqlite3.Connection,
) -> Iterator[sqlite3.Connection]:
    shared_memory_db_connection.execute("PRAGMA foreign_keys = OFF;")
    yield shared_memory_db_connection


@pytest.fixture
def initialized_shared_memory_db_connection_foreign_keys_off(
    shared_memory_db_uri: str,
    schema_path: str,
    shared_memory_db_connection_foreign_keys_off: sqlite3.Connection,
) -> sqlite3.Connection:
    initialize_database(shared_memory_db_uri, schema_path, uri=True)
    return shared_memory_db_connection_foreign_keys_off


@pytest.fixture
def initialized_shared_memory_db_uri(
    shared_memory_db_uri: str,
    initialized_shared_memory_db_connection: sqlite3.Connection,  # pylint: disable=unused-argument
) -> str:
    return shared_memory_db_uri


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Iterator[Path]:
    yield tmp_path / "test_portfolio.db"


@pytest.fixture
def tmp_db_connection(tmp_db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = open_connection(tmp_db_path)
    yield connection
    connection.close()


@pytest.fixture
def initialized_tmp_db_path(tmp_db_path: Path, schema_path: str) -> Iterator[Path]:
    initialize_database(tmp_db_path, schema_path)
    yield tmp_db_path
