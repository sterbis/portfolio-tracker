import logging
import sqlite3
from pathlib import Path


logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def initialize_database(
    database: str | Path, *, uri: bool = False
) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    connection = open_connection(database, uri=uri)
    try:
        connection.executescript(schema)
        logger.debug("'%s' database initialized successfully.", Path(database).name)

    finally:
        connection.close()


def open_connection(
    database: str | Path, *, timeout: float = 5, uri: bool = False
) -> sqlite3.Connection:
    connection = sqlite3.connect(
        database,
        timeout=timeout,
        detect_types=sqlite3.PARSE_DECLTYPES,
        uri=uri,
        autocommit=True,
    )

    connection.execute("PRAGMA foreign_keys = ON;")
    cursor = connection.execute("PRAGMA journal_mode = WAL;")

    journal_mode = cursor.fetchone()[0].upper()
    if journal_mode != "WAL":
        logger.warning(
            "Cannot set journal mode to WAL mode. Current journal mode is '%s' mode.",
            journal_mode,
        )

    return connection
