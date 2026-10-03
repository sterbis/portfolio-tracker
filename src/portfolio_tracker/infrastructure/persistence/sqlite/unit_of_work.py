import logging
import sqlite3
from functools import cached_property
from types import TracebackType
from typing import Self

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import StorageConnection, UnitOfWork
from portfolio_tracker.application.security import Encryptor

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
        user_id: str | None,
        institution_registry: InstitutionRegistry,
        encryptor: Encryptor,
        executor: SqliteExecutor,
        *,
        read_only: bool = False,
    ) -> None:
        super().__init__(user_id)
        self._institution_registry = institution_registry
        self._encryptor = encryptor
        self._executor = executor
        self._read_only = read_only
        self._is_active = False

    @cached_property
    def accounts(self) -> SqliteAccountRepository:
        return SqliteAccountRepository(self._get_user_id(), self._executor)

    @cached_property
    def credentials(self) -> SqliteCredentialsRepository:
        return SqliteCredentialsRepository(
            self._get_user_id(),
            self._executor,
            self._institution_registry,
            self._encryptor,
        )

    @cached_property
    def fx_rates(self) -> SqliteFxRatesRepository:
        return SqliteFxRatesRepository(self._executor)

    @cached_property
    def institution_connections(self) -> SqliteInstitutionConnectionRepository:
        return SqliteInstitutionConnectionRepository(
            self._get_user_id(), self._executor, self._institution_registry
        )

    @cached_property
    def instruments(self) -> SqliteInstrumentRepository:
        return SqliteInstrumentRepository(self._executor)

    @cached_property
    def market_data(self) -> SqliteMarketDataRepository:
        return SqliteMarketDataRepository(self._executor)

    @cached_property
    def transactions(self) -> SqliteTransactionRepository:
        return SqliteTransactionRepository(self._get_user_id(), self._executor)

    @cached_property
    def users(self) -> SqliteUserRepository:
        return SqliteUserRepository(self._executor)

    def __enter__(self) -> Self:
        mode = "DEFERRED" if self._read_only else "IMMEDIATE"
        self._executor.execute(f"BEGIN {mode} TRANSACTION;")
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
        self._executor.execute("COMMIT;")
        self._is_active = False

    def rollback(self) -> None:
        self._executor.execute("ROLLBACK;")
        self._is_active = False


class SqliteStorageConnection(StorageConnection):
    def __init__(
        self,
        uri: str,
        schema_registry: SchemaRegistry,
        institution_registry: InstitutionRegistry,
        encryptor: Encryptor,
        *,
        read_only: bool = False,
        timeout: float = 5,
    ) -> None:
        self._uri = uri
        self._institution_registry = institution_registry
        self._encryptor = encryptor
        self._read_only = read_only
        self._timeout = timeout
        self._builder = SqliteStatementBuilder(
            resolver=SchemaResolver(registry=schema_registry)
        )
        self._connection: sqlite3.Connection | None = None

    def __enter__(self) -> Self:
        logger.debug("Open '%s' database connection.", self._uri)
        self._connection = open_connection(
            self._uri,
            timeout=self._timeout,
            read_only=self._read_only,
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        assert self._connection is not None
        logger.debug("Close '%s' database connection.", self._uri)
        self._connection.close()
        self._connection = None

    def unit_of_work(self, user_id: str | None = None) -> SqliteUnitOfWork:
        if not self._connection:
            raise RuntimeError("Database connection not opened.")

        return SqliteUnitOfWork(
            user_id=user_id,
            institution_registry=self._institution_registry,
            encryptor=self._encryptor,
            executor=SqliteExecutor(self._connection, self._builder),
            read_only=self._read_only,
        )
