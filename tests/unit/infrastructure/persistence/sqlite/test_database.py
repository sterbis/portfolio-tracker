# pylint: disable=redefined-outer-name

import sqlite3
from collections.abc import Generator

import pytest

from portfolio_tracker.infrastructure.persistence.sqlite.database import open_connection


@pytest.fixture(scope="module")
def temp_db_connection(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[sqlite3.Connection, None, None]:
    connection = open_connection(
        (tmp_path_factory.mktemp("temp") / "portfolio.db").as_uri()
    )
    yield connection
    connection.close()


def test_no_transaction_is_implicitly_opened(
    temp_db_connection: sqlite3.Connection,
) -> None:
    assert temp_db_connection.autocommit is True
    assert not temp_db_connection.in_transaction


def test_foreign_keys_are_on(temp_db_connection: sqlite3.Connection) -> None:
    row = temp_db_connection.execute("PRAGMA foreign_keys;").fetchone()
    assert row[0] == 1


def test_journal_mode_is_wal_mode(temp_db_connection: sqlite3.Connection) -> None:
    row = temp_db_connection.execute("PRAGMA journal_mode;").fetchone()
    assert row[0] == "wal"


def test_row_factory_is_none(temp_db_connection: sqlite3.Connection) -> None:
    assert temp_db_connection.row_factory is None


def test_read_only_connection_rejects_database_writes(memory_db_uri: str) -> None:
    with open_connection(memory_db_uri, read_only=True) as connection:
        assert connection.execute("PRAGMA query_only;").fetchone()[0] == 1
        with pytest.raises(
            sqlite3.OperationalError, match="readonly database|read-only"
        ):
            connection.execute("CREATE TABLE blocked (id INTEGER);")


def test_database_initialization(
    initialized_memory_db_connection: sqlite3.Connection,
) -> None:
    cursor = initialized_memory_db_connection.cursor()

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
        "account",
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
