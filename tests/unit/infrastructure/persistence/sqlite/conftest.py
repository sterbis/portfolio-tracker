# pylint: disable=redefined-outer-name

import sqlite3
from collections.abc import Generator
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pytest

from portfolio_tracker.infrastructure.persistence.sqlite import _MIGRATIONS_DIR
from portfolio_tracker.infrastructure.persistence.sqlite.builder import (
    SqliteStatementBuilder,
)
from portfolio_tracker.infrastructure.persistence.sqlite.database import (
    apply_migrations,
    open_connection,
)
from portfolio_tracker.infrastructure.persistence.sqlite.mappers import register_mappers
from portfolio_tracker.infrastructure.persistence.sqlite.registry import (
    SCHEMA_REGISTRY,
    SchemaResolver,
)


@pytest.fixture(scope="session")
def statement_builder() -> SqliteStatementBuilder:
    return SqliteStatementBuilder(resolver=SchemaResolver(registry=SCHEMA_REGISTRY))


@pytest.fixture(scope="session", autouse=True)
def register_sqlite_mappers() -> None:
    register_mappers()


@pytest.fixture
def memory_db_uri() -> str:
    return f"file:{uuid4().hex}.db?mode=memory&cache=shared"


@pytest.fixture
def memory_db_connection(
    memory_db_uri: str,
) -> Generator[sqlite3.Connection, None, None]:
    connection = open_connection(memory_db_uri)
    yield connection
    connection.close()


@pytest.fixture
def initialized_memory_db_connection(
    memory_db_uri: str,
    memory_db_connection: sqlite3.Connection,
) -> sqlite3.Connection:
    apply_migrations(memory_db_uri, _MIGRATIONS_DIR)
    return memory_db_connection


@pytest.fixture
def initialized_memory_db_connection_foreign_keys_off(
    initialized_memory_db_connection: sqlite3.Connection,
) -> sqlite3.Connection:
    initialized_memory_db_connection.execute("PRAGMA foreign_keys = OFF;")
    return initialized_memory_db_connection


@pytest.fixture
def temp_db_uri(tmp_path: Path) -> str:
    return (tmp_path / "portfolio.db").as_uri()


@pytest.fixture
def open_initialized_temp_db_connection(
    temp_db_uri: str,
) -> Generator[Callable[..., sqlite3.Connection], None, None]:
    apply_migrations(temp_db_uri, _MIGRATIONS_DIR)
    connections: list[sqlite3.Connection] = []

    def open_(*, timeout: float = 5.0, read_only: bool = False) -> sqlite3.Connection:
        connection = open_connection(temp_db_uri, timeout=timeout, read_only=read_only)
        connections.append(connection)
        return connection

    yield open_

    for connection in connections:
        try:
            connection.close()

        except sqlite3.Error:
            pass
