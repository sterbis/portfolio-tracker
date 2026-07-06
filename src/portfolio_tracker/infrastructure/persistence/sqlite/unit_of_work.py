import logging
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Self

from portfolio_tracker.application.encryption import Encryptor
from portfolio_tracker.application.persistence import UnitOfWork
from portfolio_tracker.domain.institution import InstitutionRegistry

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
        database: str | Path,
        encryptor: Encryptor,
        institution_registry: InstitutionRegistry,
        *,
        read_only: bool = False,
        timeout: float = 5,
        uri: bool = False,
    ) -> None:
        super().__init__(institution_registry)
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

        executor = SqliteExecutor(self._connection)

        self.accounts = SqliteAccountRepository(executor)
        self.fx_rates = SqliteFxRatesRepository(executor)
        self.instruments = SqliteInstrumentRepository(executor)
        self.market_data = SqliteMarketDataRepository(executor)
        self.transactions = SqliteTransactionRepository(executor)
        self.users = SqliteUserRepository(executor)
        self.credentials = SqliteCredentialsRepository(
            self._institution_registry, self._encryptor, executor
        )

        if self._read_only:
            self._connection.execute("BEGIN TRANSACTION;")
        else:
            self._connection.execute("BEGIN IMMEDIATE TRANSACTION;")

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        assert self._connection is not None

        try:
            super().__exit__(exc_type, exc_value, traceback)
        finally:
            logger.debug("Close '%s' database connection.", self._database)
            self._connection.close()
            self._connection = None

    def commit(self) -> None:
        if self._connection:
            logger.debug("Commit '%s' database changes.", self._database)
            self._connection.execute("COMMIT;")

    def rollback(self) -> None:
        if self._connection:
            logger.debug("Rollback '%s' database changes.", self._database)
            self._connection.execute("ROLLBACK;")
