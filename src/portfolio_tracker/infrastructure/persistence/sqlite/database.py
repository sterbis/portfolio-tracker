import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from .executor import SqliteExecutor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MigrationFile:
    version: int
    name: str
    path: Path



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


def apply_migrations(uri: str, migrations_dir: Path) -> None:
    migrations = _get_available_migrations(migrations_dir)
    if not migrations:
        raise RuntimeError(f"No SQL migrations found in '{migrations_dir}'.")

    connection = open_connection(uri)
    executor = SqliteExecutor(connection)

    try:
        executor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migration (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at DATETIME NOT NULL
            );
        """)

        executor.execute("BEGIN IMMEDIATE TRANSACTION;")
        cursor = executor.execute("SELECT version FROM schema_migration;")
        applied_versions = {row[0] for row in cursor.fetchall()}
        latest_available_version = migrations[-1].version
        latest_applied_version = max(applied_versions, default=0)
        if latest_applied_version > latest_available_version:
            raise RuntimeError(
                "Database schema version "
                f"{latest_applied_version} is newer than the latest available "
                f"migration version {latest_available_version}."
            )

        for migration in migrations:
            if migration.version in applied_versions:
                continue

            migration_sql = migration.path.read_text(encoding="utf-8")
            executor.execute_script(migration_sql)
            executor.execute(
                "INSERT INTO schema_migration (version, name, applied_at) VALUES (:version, :name, :applied_at);",
                {
                    "version": migration.version,
                    "name": migration.name,
                    "applied_at": datetime.now(tz=timezone.utc),
                },
            )

        executor.execute("COMMIT;")

    except Exception:
        if connection.in_transaction:
            executor.execute("ROLLBACK;")
        raise

    finally:
        connection.close()


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


def _get_available_migrations(migrations_dir: Path) -> list[MigrationFile]:
    migration_files: list[MigrationFile] = []
    pattern = re.compile(r"^(\d{4})_(.+)\.sql$")

    for path in sorted(migrations_dir.glob("*.sql")):
        match = pattern.match(path.name)
        if match:
            version = int(match.group(1))
            migration_files.append(
                MigrationFile(version=version, name=path.name, path=path)
            )

    return sorted(migration_files, key=lambda file: file.version)
