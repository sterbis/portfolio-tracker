import logging
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Self

from portfolio_tracker.application.ports.unit_of_work import UnitOfWork

from .database import open_connection
from .executor import SqliteExecutor
from .repositories import (
    SqliteAccountRepository,
    SqliteFxRatesRepository,
    SqliteInstrumentRepository,
    SqliteMarketDataRepository,
    SqliteTransactionRepository,
    SqliteUserRepository,
)

logger = logging.getLogger(__name__)


class SqliteUnitOfWork(UnitOfWork):
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None

    def __enter__(self) -> Self:
        logger.debug("Open '%s' database connection.", self._db_path.name)
        self._connection = open_connection(self._db_path)

        executor = SqliteExecutor(self._connection)

        self.accounts = SqliteAccountRepository(executor)
        self.fx_rates = SqliteFxRatesRepository(executor)
        self.instruments = SqliteInstrumentRepository(executor)
        self.market_data = SqliteMarketDataRepository(executor)
        self.transactions = SqliteTransactionRepository(executor)
        self.users = SqliteUserRepository(executor)

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
            logger.debug("Close '%s' database connection.", self._db_path.name)
            self._connection.close()
            self._connection = None

    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError(f"'{self._db_path}' database connection is not opened.")

        return self._connection

    def commit(self) -> None:
        if self._connection:
            logger.debug("Commit '%s' database changes.", self._db_path.name)
            self._connection.commit()

    def rollback(self) -> None:
        if self._connection:
            logger.debug("Rollback '%s' database changes.", self._db_path.name)
            self._connection.rollback()
