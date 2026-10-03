from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Callable, TypeVar

from filterutils import Filter

from portfolio_tracker.application.institution.registry import InstitutionRegistry
from portfolio_tracker.application.shared.errors import (
    AssetAccountNotFoundError,
    CredentialsNotFoundError,
    EntityNotFoundError,
    FxDataIntegrityError,
    InstitutionConnectionNotFoundError,
    TransactionNotFoundError,
)
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.account import (
    AccountMap,
    AssetAccount,
)
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.institution import Credentials, InstitutionConnection
from portfolio_tracker.domain.instrument import Instrument, InstrumentMetadata
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.domain.transaction import Transaction
from portfolio_tracker.domain.user import User

TEntity = TypeVar("TEntity")


PERSISTED_MODEL_TYPES = (
    User,
    InstitutionConnection,
    AssetAccount,
    Instrument,
    Transaction,
    FxRates,
    StockSplits,
)


def get_by_id_required(
    get_by_id: Callable[[str], TEntity | None],
    entity_id: str,
    error_cls: type[EntityNotFoundError],
) -> TEntity:
    entity = get_by_id(entity_id)
    if entity is None:
        raise error_cls(entity_id)

    return entity


def ensure_record_affected(
    affected_record_count: int, entity_id: str, error_cls: type[EntityNotFoundError]
) -> None:
    if affected_record_count == 0:
        raise error_cls(entity_id)


class UserScopedRepository(ABC):
    def __init__(self, user_id: str) -> None:
        self._user_id = user_id


class UserReadRepository(ABC):
    @abstractmethod
    def get_by_username(self, username: str) -> User | None: ...


class UserRepository(UserReadRepository):
    @abstractmethod
    def add(self, user: User) -> None: ...


class InstitutionConnectionReadRepository(UserScopedRepository):
    @abstractmethod
    def get_by_id(self, connection_id: str) -> InstitutionConnection | None: ...

    def get_by_id_required(self, connection_id: str) -> InstitutionConnection:
        return get_by_id_required(
            self.get_by_id, connection_id, InstitutionConnectionNotFoundError
        )

    @abstractmethod
    def get_by_ids(self, connection_ids: set[str]) -> list[InstitutionConnection]: ...

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> list[InstitutionConnection]: ...


class InstitutionConnectionRepository(InstitutionConnectionReadRepository):
    @abstractmethod
    def add(self, connection: InstitutionConnection) -> None: ...

    @abstractmethod
    def update(self, connection: InstitutionConnection) -> int: ...

    def update_required(self, connection: InstitutionConnection) -> None:
        ensure_record_affected(
            self.update(connection), connection.id, InstitutionConnectionNotFoundError
        )

    @abstractmethod
    def remove_by_id(self, connection_id: str) -> int: ...

    def remove_by_id_required(self, connection_id: str) -> None:
        ensure_record_affected(
            self.remove_by_id(connection_id),
            connection_id,
            InstitutionConnectionNotFoundError,
        )


class CredentialsReadRepository(UserScopedRepository):
    def __init__(self, user_id: str, institution_registry: InstitutionRegistry) -> None:
        super().__init__(user_id)
        self._institution_registry = institution_registry

    @abstractmethod
    def get(self, institution_connection_id: str) -> Credentials | None: ...

    def get_required(self, institution_connection_id: str) -> Credentials:
        return get_by_id_required(
            self.get, institution_connection_id, CredentialsNotFoundError
        )

    @abstractmethod
    def get_by_ids(self, institution_connection_ids: set[str]) -> list[Credentials]: ...


class CredentialsRepository(CredentialsReadRepository):
    @abstractmethod
    def upsert(self, credentials: Credentials) -> None: ...

    @abstractmethod
    def remove(self, institution_connection_id: str) -> int: ...

    def remove_required(self, connection_id: str) -> None:
        ensure_record_affected(
            self.remove(connection_id),
            connection_id,
            CredentialsNotFoundError,
        )


class AccountReadRepository(UserScopedRepository):
    @abstractmethod
    def get_by_id(self, account_id: str) -> AssetAccount | None: ...

    def get_by_id_required(self, account_id: str) -> AssetAccount:
        return get_by_id_required(self.get_by_id, account_id, AssetAccountNotFoundError)

    @abstractmethod
    def get_by_external_id(
        self, institution_connection_id: str, external_id: str
    ) -> AssetAccount | None: ...

    @abstractmethod
    def get_by_ids(self, account_ids: set[str]) -> list[AssetAccount]: ...

    @abstractmethod
    def get_by_institution_connection_id(
        self, institution_connection_id: str
    ) -> list[AssetAccount]: ...

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> list[AssetAccount]: ...

    @abstractmethod
    def get_account_map(self, user_id: str) -> AccountMap: ...


class AccountRepository(AccountReadRepository):
    @abstractmethod
    def ensure(self, account: AssetAccount) -> None: ...

    @abstractmethod
    def update(self, account: AssetAccount) -> int: ...

    def update_required(self, account: AssetAccount) -> None:
        ensure_record_affected(
            self.update(account), account.id, AssetAccountNotFoundError
        )


class InstrumentReadRepository(ABC):
    @abstractmethod
    def get(
        self,
        *,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Instrument]: ...

    @abstractmethod
    def get_metadata(
        self,
        *,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[InstrumentMetadata]: ...

    @abstractmethod
    def get_by_ids(self, instrument_ids: set[str]) -> list[Instrument]: ...

    @abstractmethod
    def get_ids_by_symbols(self, symbols: set[str]) -> set[str]: ...


class InstrumentRepository(InstrumentReadRepository):
    @abstractmethod
    def ensure(self, instrument: Instrument) -> None: ...

    @abstractmethod
    def update_last_synced_at(
        self, instrument_id: str, last_synced_at: datetime
    ) -> None: ...


class TransactionReadRepository(UserScopedRepository):
    @abstractmethod
    def get(
        self,
        *,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Transaction]: ...

    @abstractmethod
    def get_by_id(self, transaction_id: str) -> Transaction | None: ...

    def get_by_id_required(self, transaction_id: str) -> Transaction:
        return get_by_id_required(
            self.get_by_id, transaction_id, TransactionNotFoundError
        )

    @abstractmethod
    def get_distinct_dates(self, filter_: Filter | None = None) -> set[date]: ...

    @abstractmethod
    def get_distinct_instrument_ids(
        self, filter_: Filter | None = None
    ) -> set[str]: ...

    @abstractmethod
    def exists(self, transaction_id: str) -> bool: ...


class TransactionRepository(TransactionReadRepository):
    @abstractmethod
    def add(self, transaction: Transaction) -> None: ...

    @abstractmethod
    def ensure(self, transaction: Transaction) -> None: ...

    @abstractmethod
    def update(self, transaction: Transaction) -> int: ...

    def update_required(self, transaction: Transaction) -> None:
        ensure_record_affected(
            self.update(transaction), transaction.id, TransactionNotFoundError
        )

    @abstractmethod
    def remove(self, filter_: Filter) -> int: ...

    @abstractmethod
    def remove_by_id(self, transaction_id: str) -> int: ...

    def remove_by_id_required(self, transaction_id: str) -> None:
        ensure_record_affected(
            self.remove_by_id(transaction_id), transaction_id, TransactionNotFoundError
        )

    @abstractmethod
    def remove_by_account_id(self, account_id: str) -> int: ...

    def remove_by_account_id_required(self, account_id: str) -> None:
        ensure_record_affected(
            self.remove_by_account_id(account_id), account_id, AssetAccountNotFoundError
        )


class FxRatesReadRepository(ABC):
    @abstractmethod
    def get_by_date(self, effective_on: date) -> FxRates | None: ...

    @abstractmethod
    def get_by_dates(self, dates: set[date]) -> list[FxRates]: ...

    @abstractmethod
    def get_latest(self) -> FxRates | None: ...

    @abstractmethod
    def get_distinct_dates(self) -> set[date]: ...

    @abstractmethod
    def get_missing_dates(
        self,
        required_dates: set[date],
        base_currency: Currency,
        quote_currencies: set[Currency],
    ) -> set[date]: ...

    def get_by_dates_required(self, dates: set[date]) -> dict[date, FxRates]:
        rates_list = self.get_by_dates(dates)
        rates_by_date = {rates.effective_on: rates for rates in rates_list}
        if missing_dates := dates - rates_by_date.keys():
            formatted_dates = ", ".join(
                missing_date.isoformat() for missing_date in sorted(missing_dates)
            )
            raise FxDataIntegrityError(
                detail=(
                    f"Missing historical FX rates for following dates {formatted_dates}."
                ),
            )

        return rates_by_date


class FxRatesRepository(FxRatesReadRepository):
    @abstractmethod
    def ensure(self, rates: FxRates) -> None: ...


class MarketDataReadRepository(ABC):
    @abstractmethod
    def get_stock_splits_by_instrument_ids(
        self, instrument_ids: set[str]
    ) -> list[StockSplits]: ...


class MarketDataRepository(MarketDataReadRepository):
    @abstractmethod
    def ensure_stock_splits(self, splits: StockSplits) -> None: ...
