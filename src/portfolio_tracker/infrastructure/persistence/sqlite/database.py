import logging
import sqlite3
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def initialize_database(database: str | Path, *, uri: bool = False) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    connection = open_connection(database, uri=uri)
    try:
        connection.executescript(schema)
        logger.debug("'%s' database initialized successfully.", Path(database).name)

    finally:
        connection.close()


def open_connection(
    database: str | Path,
    *,
    timeout: float = 5,
    uri: bool = False,
    read_only: bool = False,
) -> sqlite3.Connection:
    if read_only:
        database, uri = _as_read_only_database(database, uri)

    connection = sqlite3.connect(
        database,
        timeout=timeout,
        detect_types=sqlite3.PARSE_DECLTYPES,
        uri=uri,
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


def _as_read_only_database(database: str | Path, uri: bool) -> tuple[str | Path, bool]:
    database_string = str(database)
    if not uri and database_string != ":memory:":
        return f"{Path(database).resolve().as_uri()}?mode=ro", True

    if not uri:
        return database, False

    parsed_uri = urlsplit(database_string)
    query_parameters = parse_qsl(parsed_uri.query, keep_blank_values=True)
    if any(name == "mode" and value == "memory" for name, value in query_parameters):
        return database, True
    if parsed_uri.path in (":memory:", "::memory:"):
        return database, True

    parameters = dict(query_parameters)
    parameters["mode"] = "ro"
    return (
        urlunsplit(
            (
                parsed_uri.scheme,
                parsed_uri.netloc,
                parsed_uri.path,
                urlencode(parameters),
                parsed_uri.fragment,
            )
        ),
        True,
    )
