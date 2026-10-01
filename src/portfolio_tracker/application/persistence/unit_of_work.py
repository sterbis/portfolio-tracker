from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from .repositories import (
    AccountRepository,
    AccountReadRepository,
    CredentialsRepository,
    CredentialsReadRepository,
    FxRatesRepository,
    FxRatesReadRepository,
    InstitutionConnectionRepository,
    InstitutionConnectionReadRepository,
    InstrumentRepository,
    InstrumentReadRepository,
    MarketDataRepository,
    MarketDataReadRepository,
    TransactionRepository,
    TransactionReadRepository,
    UserRepository,
    UserReadRepository,
)


class ReadUnitOfWork(ABC):
    accounts: AccountReadRepository
    credentials: CredentialsReadRepository
    fx_rates: FxRatesReadRepository
    institution_connections: InstitutionConnectionReadRepository
    instruments: InstrumentReadRepository
    market_data: MarketDataReadRepository
    transactions: TransactionReadRepository
    users: UserReadRepository

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id

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
    def rollback(self) -> None: ...


class UnitOfWork(ReadUnitOfWork):
    accounts: AccountRepository
    fx_rates: FxRatesRepository
    institution_connections: InstitutionConnectionRepository
    instruments: InstrumentRepository
    market_data: MarketDataRepository
    transactions: TransactionRepository
    users: UserRepository
    credentials: CredentialsRepository

    @abstractmethod
    def commit(self) -> None: ...


class StorageReadConnection(ABC):
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
    def unit_of_work(self, user_id: str) -> ReadUnitOfWork: ...


class StorageConnection(StorageReadConnection):
    @abstractmethod
    def unit_of_work(self, user_id: str) -> UnitOfWork: ...


class StorageConnectionFactory(ABC):
    @abstractmethod
    def create(self, *, read_only: bool = False) -> StorageReadConnection | StorageConnection: ...
