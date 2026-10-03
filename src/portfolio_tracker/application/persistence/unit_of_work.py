from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from portfolio_tracker.application.shared.errors import UserNotLoggedInError

from .repositories import (
    AccountReadRepository,
    AccountRepository,
    CredentialsReadRepository,
    CredentialsRepository,
    FxRatesReadRepository,
    FxRatesRepository,
    InstitutionConnectionReadRepository,
    InstitutionConnectionRepository,
    InstrumentReadRepository,
    InstrumentRepository,
    MarketDataReadRepository,
    MarketDataRepository,
    TransactionReadRepository,
    TransactionRepository,
    UserReadRepository,
    UserRepository,
)


class ReadUnitOfWork(ABC):
    def __init__(self, user_id: str | None = None) -> None:
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

    @property
    @abstractmethod
    def accounts(self) -> AccountReadRepository: ...

    @property
    @abstractmethod
    def credentials(self) -> CredentialsReadRepository: ...

    @property
    @abstractmethod
    def fx_rates(self) -> FxRatesReadRepository: ...

    @property
    @abstractmethod
    def institution_connections(self) -> InstitutionConnectionReadRepository: ...

    @property
    @abstractmethod
    def instruments(self) -> InstrumentReadRepository: ...

    @property
    @abstractmethod
    def market_data(self) -> MarketDataReadRepository: ...

    @property
    @abstractmethod
    def transactions(self) -> TransactionReadRepository: ...

    @property
    @abstractmethod
    def users(self) -> UserReadRepository: ...

    @abstractmethod
    def rollback(self) -> None: ...

    def _get_user_id(self) -> str:
        if self._user_id is None:
            raise UserNotLoggedInError()

        return self._user_id


class UnitOfWork(ReadUnitOfWork):
    @property
    @abstractmethod
    def accounts(self) -> AccountRepository: ...

    @property
    @abstractmethod
    def credentials(self) -> CredentialsRepository: ...

    @property
    @abstractmethod
    def fx_rates(self) -> FxRatesRepository: ...

    @property
    @abstractmethod
    def institution_connections(self) -> InstitutionConnectionRepository: ...

    @property
    @abstractmethod
    def instruments(self) -> InstrumentRepository: ...

    @property
    @abstractmethod
    def market_data(self) -> MarketDataRepository: ...

    @property
    @abstractmethod
    def transactions(self) -> TransactionRepository: ...

    @property
    @abstractmethod
    def users(self) -> UserRepository: ...

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
    def unit_of_work(self, user_id: str | None = None) -> ReadUnitOfWork: ...


class StorageConnection(StorageReadConnection):
    @abstractmethod
    def unit_of_work(self, user_id: str | None = None) -> UnitOfWork: ...
