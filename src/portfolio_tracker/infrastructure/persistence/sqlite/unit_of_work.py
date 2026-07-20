import logging
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Self

from portfolio_tracker.application.encryption import Encryptor
from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import (
    Session,
    SessionFactory,
    UnitOfWork,
)

from .database import open_connection
from .executor import SqliteExecutor
from .repositories import (
    SqliteAccountRepository,
    SqliteCredentialsRepository,
    SqliteFxRatesRepository,
    SqliteInstrumentRepository,
    SqliteMarketDataRepository,
    SqliteTransactionRepository,
    SqliteUserRepository,
)

logger = logging.getLogger(__name__)


class SqliteUnitOfWork(UnitOfWork):
    def __init__(
        self,
        connection: sqlite3.Connection,
        encryptor: Encryptor,
        institution_registry: InstitutionRegistry,
        *,
        read_only: bool = False,
    ) -> None:
        self._connection = connection
        super().__init__(institution_registry)
        self._encryptor = encryptor
        self._read_only = read_only
        self._active = False

    def __enter__(self) -> Self:
        executor = SqliteExecutor(self._connection)

        self.accounts = SqliteAccountRepository(self._institution_registry, executor)
        self.fx_rates = SqliteFxRatesRepository(executor)
        self.instruments = SqliteInstrumentRepository(executor)
        self.market_data = SqliteMarketDataRepository(executor)
        self.transactions = SqliteTransactionRepository(executor)
        self.users = SqliteUserRepository(executor)
        self.credentials = SqliteCredentialsRepository(
            self._institution_registry, self._encryptor, executor
        )

        mode = "DEFERRED" if self._read_only else "IMMEDIATE"

        logger.debug("Begin %s database transaction.", mode.lower())
        self._connection.execute(f"BEGIN {mode} TRANSACTION;")
        self._active = True

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._active:
            self.rollback()

    def commit(self) -> None:
        logger.debug("Commit database changes.")
        self._connection.execute("COMMIT;")
        self._active = False

    def rollback(self) -> None:
        logger.debug("Rollback database changes.")
        self._connection.execute("ROLLBACK;")
        self._active = False


class SqliteSession(Session):
    def __init__(
        self,
        database: str | Path,
        encryptor: Encryptor,
        institution_registry: InstitutionRegistry,
        *,
        read_only: bool = False,
        timeout: float = 5,
        uri: bool = False,
    ) -> None:
        self._institution_registry = institution_registry
        self._database = database
        self._encryptor = encryptor
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
            connection=self._connection,
            encryptor=self._encryptor,
            institution_registry=self._institution_registry,
            read_only=self._read_only,
        )


class SqliteSessionFactory(SessionFactory):
    def __init__(
        self,
        database: str | Path,
        encryptor: Encryptor,
        institution_registry: InstitutionRegistry,
        *,
        timeout: float = 5,
        uri: bool = False,
    ) -> None:
        self._institution_registry = institution_registry
        self._database = database
        self._encryptor = encryptor
        self._timeout = timeout
        self._uri = uri

    def create(self, read_only: bool = False) -> SqliteSession:
        return SqliteSession(
            database=self._database,
            encryptor=self._encryptor,
            institution_registry=self._institution_registry,
            timeout=self._timeout,
            uri=self._uri,
            read_only=read_only,
        )
