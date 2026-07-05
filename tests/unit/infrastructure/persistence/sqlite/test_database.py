import sqlite3


def test_no_transaction_is_implicitly_opened(
    memory_db_connection: sqlite3.Connection,
) -> None:
    assert memory_db_connection.autocommit is True
    assert memory_db_connection.in_transaction is False


def test_foreign_keys_are_on(memory_db_connection: sqlite3.Connection) -> None:
    row = memory_db_connection.execute("PRAGMA foreign_keys;").fetchone()
    assert row is not None
    assert row[0] == 1


def test_journal_mode_is_wal_mode(tmp_db_connection: sqlite3.Connection) -> None:
    row = tmp_db_connection.execute("PRAGMA journal_mode;").fetchone()
    assert row is not None
    assert row[0] == "wal"


def test_database_initialization(
    initialized_shared_memory_db_connection: sqlite3.Connection,
) -> None:
    cursor = initialized_shared_memory_db_connection.cursor()

    cursor.execute("""
        SELECT name 
        FROM sqlite_schema 
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%';
    """)

    tables = [row[0] for row in cursor.fetchall()]
    assert tables == [
        "user",
        "institution_account",
        "credentials",
        "asset_account",
        "instrument",
        "bond",
        "cfd",
        "commodity",
        "crypto",
        "etf",
        "future",
        "option",
        "stock",
        "ledger_entry",
        "fx_rate",
        "stock_split",
    ]
