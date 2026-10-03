import logging
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def initialize_database(uri: str) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    connection = open_connection(uri)
    try:
        connection.executescript(schema)
        logger.debug("'%s' database initialized successfully.", uri)

    finally:
        connection.close()


def open_connection(
    uri: str, *, timeout: float = 5, read_only: bool = False
) -> sqlite3.Connection:
    if read_only:
        uri = _as_read_only_connection(uri)

    connection = sqlite3.connect(
        uri,
        timeout=timeout,
        detect_types=sqlite3.PARSE_DECLTYPES,
        uri=True,
        autocommit=True,
    )

    connection.execute("PRAGMA foreign_keys = ON;")
    if read_only:
        connection.execute("PRAGMA query_only = ON;")
        return connection

    cursor = connection.execute("PRAGMA journal_mode = WAL;")
    journal_mode = cursor.fetchone()[0].upper()
    if journal_mode != "WAL":
        logger.warning(
            "Cannot set journal mode to WAL mode. Current journal mode is '%s' mode.",
            journal_mode,
        )

    return connection


def _as_read_only_connection(uri: str) -> str:
    parts = urlsplit(uri)
    query_parameters = parse_qs(parts.query, keep_blank_values=True)

    if parts.path == ":memory:" or query_parameters.get("mode") == ["memory"]:
        return uri

    if query_parameters.get("mode") == ["ro"]:
        return uri

    query_parameters["mode"] = ["ro"]
    query = urlencode(query_parameters, doseq=True)

    return urlunsplit(parts._replace(query=query))
