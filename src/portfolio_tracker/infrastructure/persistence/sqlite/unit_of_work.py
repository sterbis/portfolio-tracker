import logging
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Self

from portfolio_tracker.application.encryption import Encryptor
from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import (
    StorageConnection,
    StorageConnectionFactory,
    UnitOfWork,
)

from .builder import SqliteStatementBuilder
from .database import open_connection
from .executor import SqliteExecutor
from .registry import SchemaRegistry, SchemaResolver
from .repositories import (
    SqliteAccountRepository,
    SqliteCredentialsRepository,
    SqliteFxRatesRepository,
    SqliteInstitutionConnectionRepository,
    SqliteInstrumentRepository,
    SqliteMarketDataRepository,
    SqliteTransactionRepository,
    SqliteUserRepository,
)

logger = logging.getLogger(__name__)


class SqliteUnitOfWork(UnitOfWork):
    def __init__(
        self,
        institution_registry: InstitutionRegistry,
        encryptor: Encryptor,
        builder: SqliteStatementBuilder,
        connection: sqlite3.Connection,
        *,
        read_only: bool = False,
    ) -> None:
        super().__init__(institution_registry)
        self._connection = connection
        self._encryptor = encryptor
        self._builder = builder
        self._read_only = read_only
        self._is_active = False

        executor = SqliteExecutor(self._connection, self._builder)

        self.accounts = SqliteAccountRepository(executor)
        self.fx_rates = SqliteFxRatesRepository(executor)
        self.institution_connections = SqliteInstitutionConnectionRepository(
            self._institution_registry, executor
        )
        self.instruments = SqliteInstrumentRepository(executor)
        self.market_data = SqliteMarketDataRepository(executor)
        self.transactions = SqliteTransactionRepository(executor)
        self.users = SqliteUserRepository(executor)
        self.credentials = SqliteCredentialsRepository(
            self._institution_registry, self._encryptor, executor
        )

    def __enter__(self) -> Self:
        mode = "DEFERRED" if self._read_only else "IMMEDIATE"
        logger.debug("Begin %s database transaction.", mode.lower())
        self._connection.execute(f"BEGIN {mode} TRANSACTION;")
        self._is_active = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._is_active:
            self.rollback()

    def commit(self) -> None:
        logger.debug("Commit database changes.")
        self._connection.execute("COMMIT;")
        self._is_active = False

    def rollback(self) -> None:
        logger.debug("Rollback database changes.")
        self._connection.execute("ROLLBACK;")
        self._is_active = False


class SqliteStorageConnection(StorageConnection):
    def __init__(
        self,
        database: str | Path,
        encryptor: Encryptor,
        builder: SqliteStatementBuilder,
        institution_registry: InstitutionRegistry,
        *,
        read_only: bool = False,
        timeout: float = 5,
        uri: bool = False,
    ) -> None:
        self._database = database
        self._encryptor = encryptor
        self._builder = builder
        self._institution_registry = institution_registry
        self._read_only = read_only
        self._timeout = timeout
        self._uri = uri
        self._connection: sqlite3.Connection | None = None

    def __enter__(self) -> Self:
        logger.debug("Open '%s' database connection.", self._database)
        self._connection = open_connection(
            self._database, timeout=self._timeout, uri=self._uri
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        assert self._connection is not None
        logger.debug("Close '%s' database connection.", self._database)
        self._connection.close()
        self._connection = None

    def unit_of_work(self) -> SqliteUnitOfWork:
        if not self._connection:
            raise RuntimeError("Database connection not opened.")

        return SqliteUnitOfWork(
            institution_registry=self._institution_registry,
            encryptor=self._encryptor,
            builder=self._builder,
            connection=self._connection,
            read_only=self._read_only,
        )


class SqliteStorageConnectionFactory(StorageConnectionFactory):
    def __init__(
        self,
        database: str | Path,
        encryptor: Encryptor,
        institution_registry: InstitutionRegistry,
        schema_registry: SchemaRegistry,
        *,
        timeout: float = 5,
        uri: bool = False,
    ) -> None:
        self._database = database
        self._encryptor = encryptor
        self._institution_registry = institution_registry
        self._timeout = timeout
        self._uri = uri

        self._builder = SqliteStatementBuilder(
            resolver=SchemaResolver(registry=schema_registry)
        )

    def create(self, *, read_only: bool = False) -> SqliteStorageConnection:
        return SqliteStorageConnection(
            database=self._database,
            encryptor=self._encryptor,
            builder=self._builder,
            institution_registry=self._institution_registry,
            timeout=self._timeout,
            uri=self._uri,
            read_only=read_only,
        )
