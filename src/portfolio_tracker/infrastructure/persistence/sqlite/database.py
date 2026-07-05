import logging
import sqlite3
from pathlib import Path

from .mappers import register_mappers

logger = logging.getLogger(__name__)


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
    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")

    return connection


def initialize_database(
    database: str | Path, schema_path: str | Path, *, uri: bool = False
) -> None:
    schema = Path(schema_path).read_text(encoding="utf-8")
    connection = open_connection(database, uri=uri)
    try:
        connection.executescript(schema)
        logger.debug("'%s' database initialized successfully.", Path(database).name)
    finally:
        connection.close()

    register_mappers()
