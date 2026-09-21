from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from portfolio_tracker.application.institution import InstitutionRegistry

from .repositories import (
    AccountRepository,
    CredentialsRepository,
    FxRatesRepository,
    InstitutionConnectionRepository,
    InstrumentRepository,
    MarketDataRepository,
    TransactionRepository,
    UserRepository,
)


class UnitOfWork(ABC):
    accounts: AccountRepository
    fx_rates: FxRatesRepository
    institution_connections: InstitutionConnectionRepository
    instruments: InstrumentRepository
    market_data: MarketDataRepository
    transactions: TransactionRepository
    users: UserRepository
    credentials: CredentialsRepository

    def __init__(
        self,
        institution_registry: InstitutionRegistry,
    ) -> None:
        self._institution_registry = institution_registry

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.rollback()

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...


class StorageConnection(ABC):
    @abstractmethod
    def __enter__(self) -> Self: ...

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    def unit_of_work(self) -> UnitOfWork: ...


class StorageConnectionFactory(ABC):
    @abstractmethod
    def create(self, *, read_only: bool = False) -> StorageConnection: ...
