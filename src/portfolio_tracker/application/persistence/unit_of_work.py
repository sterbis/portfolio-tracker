from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from portfolio_tracker.application.institution import InstitutionRegistry

from .credentials_store import CredentialsStore
from .repositories import (
    AccountRepository,
    FxRatesRepository,
    InstrumentRepository,
    MarketDataRepository,
    TransactionRepository,
    UserRepository,
)


class UnitOfWork(ABC):
    accounts: AccountRepository
    fx_rates: FxRatesRepository
    instruments: InstrumentRepository
    market_data: MarketDataRepository
    transactions: TransactionRepository
    users: UserRepository
    credentials: CredentialsStore

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
        if exc_type is not None:
            self.rollback()

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
