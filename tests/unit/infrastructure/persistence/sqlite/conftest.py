# pylint: disable=redefined-outer-name

import sqlite3
from collections.abc import Generator
from pathlib import Path
from typing import Callable

import pytest

from portfolio_tracker.infrastructure.persistence.sqlite.builder import (
    SqliteStatementBuilder,
)
from portfolio_tracker.infrastructure.persistence.sqlite.database import (
    initialize_database,
    open_connection,
)
from portfolio_tracker.infrastructure.persistence.sqlite.mappers import register_mappers
from portfolio_tracker.infrastructure.persistence.sqlite.registry import (
    SCHEMA_REGISTRY,
    SchemaResolver,
)


@pytest.fixture(scope="session", autouse=True)
def register_sqlite_mappers() -> None:
    register_mappers()


@pytest.fixture
def in_memory_db_uri() -> str:
    return "file:test_db?mode=memory&cache=shared"


@pytest.fixture
def in_memory_db_connection(
    in_memory_db_uri: str,
) -> Generator[sqlite3.Connection, None, None]:
    connection = open_connection(in_memory_db_uri, uri=True)
    yield connection
    connection.close()


@pytest.fixture
def initialized_in_memory_db_connection(
    in_memory_db_uri: str,
    in_memory_db_connection: sqlite3.Connection,
) -> sqlite3.Connection:
    initialize_database(in_memory_db_uri, uri=True)
    return in_memory_db_connection


@pytest.fixture
def initialized_in_memory_db_connection_foreign_keys_off(
    initialized_in_memory_db_connection: sqlite3.Connection,
) -> sqlite3.Connection:
    initialized_in_memory_db_connection.execute("PRAGMA foreign_keys = OFF;")
    return initialized_in_memory_db_connection


@pytest.fixture
def open_initialized_db_connection(
    tmp_path: Path,
) -> Generator[Callable[..., sqlite3.Connection], None, None]:
    db_path = tmp_path / "portfolio.db"
    initialize_database(db_path)

    connections: list[sqlite3.Connection] = []

    def open_(timeout: float = 5.0) -> sqlite3.Connection:
        connection = open_connection(db_path, timeout=timeout)
        connections.append(connection)
        return connection

    yield open_

    for connection in connections:
        try:
            connection.close()

        except sqlite3.Error:
            pass


@pytest.fixture(scope="session")
def statement_builder() -> SqliteStatementBuilder:
    return SqliteStatementBuilder(
        resolver=SchemaResolver(
            registry=SCHEMA_REGISTRY,
        )
    )
