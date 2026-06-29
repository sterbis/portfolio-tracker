import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def open_connection(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path, autocommit=True)
    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")

    return connection


def initialize_database(db_path: str | Path, schema_path: str | Path) -> None:
    schema = Path(schema_path).read_text(encoding="utf-8")
    connection = open_connection(db_path)
    try:
        connection.executescript(schema)
        connection.commit()
        logger.debug("'%s' database initialized successfully.", Path(db_path).name)
    finally:
        connection.close()
