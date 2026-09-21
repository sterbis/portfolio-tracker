# pylint: disable=redefined-outer-name

import sqlite3
from collections.abc import Generator

import pytest

from portfolio_tracker.infrastructure.persistence.sqlite.database import open_connection


@pytest.fixture(scope="module")
def db_connection(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[sqlite3.Connection, None, None]:
    connection = open_connection(tmp_path_factory.mktemp("tmp") / "test.db")
    yield connection
    connection.close()


def test_no_transaction_is_implicitly_opened(
    db_connection: sqlite3.Connection,
) -> None:
    assert db_connection.autocommit is True
    assert not db_connection.in_transaction


def test_foreign_keys_are_on(db_connection: sqlite3.Connection) -> None:
    row = db_connection.execute("PRAGMA foreign_keys;").fetchone()
    assert row[0] == 1


def test_journal_mode_is_wal_mode(db_connection: sqlite3.Connection) -> None:
    row = db_connection.execute("PRAGMA journal_mode;").fetchone()
    assert row[0] == "wal"


def test_row_factory_is_none(db_connection: sqlite3.Connection) -> None:
    assert db_connection.row_factory is None


def test_database_initialization(
    initialized_in_memory_db_connection: sqlite3.Connection,
) -> None:
    cursor = initialized_in_memory_db_connection.cursor()

    cursor.execute("""
        SELECT name 
        FROM sqlite_schema 
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%';
    """)

    tables = [row[0] for row in cursor.fetchall()]
    assert tables == [
        "user",
        "institution_connection",
        "credentials",
        "asset_account",
        "ledger",
        "instrument",
        "bond",
        "cfd",
        "commodity",
        "crypto",
        "etf",
        "future",
        "option",
        "stock",
        "fx_rate",
        "stock_split",
    ]
