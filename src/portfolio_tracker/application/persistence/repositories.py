from abc import ABC, abstractmethod
from datetime import date, datetime

from filterutils import Filter

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.shared.errors import FxDataIntegrityError
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.account import (
    AccountMap,
    AssetAccount,
)
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.institution import Credentials, InstitutionConnection
from portfolio_tracker.domain.instrument import Instrument, InstrumentMetadata
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.transaction import Transaction
from portfolio_tracker.domain.user import User

PERSISTED_MODEL_TYPES = (
    User,
    InstitutionConnection,
    AssetAccount,
    Instrument,
    Transaction,
    FxRates,
    StockSplits,
)


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> None: ...

    @abstractmethod
    def get_by_username(self, username: str) -> User | None: ...


class InstitutionConnectionRepository(ABC):
    @abstractmethod
    def add(self, connection: InstitutionConnection) -> None: ...

    @abstractmethod
    def get_by_id(self, connection_id: str) -> InstitutionConnection | None: ...

    @abstractmethod
    def get_by_ids(self, connection_ids: set[str]) -> list[InstitutionConnection]: ...

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> list[InstitutionConnection]: ...

    @abstractmethod
    def update(self, connection: InstitutionConnection) -> None: ...

    @abstractmethod
    def remove_by_id(self, connection_id: str) -> None: ...


class CredentialsRepository(ABC):
    def __init__(self, institution_registry: InstitutionRegistry) -> None:
        self._institution_registry = institution_registry

    @abstractmethod
    def upsert(self, credentials: Credentials) -> None: ...

    @abstractmethod
    def get(self, institution_connection_id: str) -> Credentials | None: ...

    @abstractmethod
    def remove(self, institution_connection_id: str) -> None: ...


class AccountRepository(ABC):
    @abstractmethod
    def ensure(self, account: AssetAccount) -> None: ...

    @abstractmethod
    def get_by_id(self, account_id: str) -> AssetAccount | None: ...

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
    def update(self, account: AssetAccount) -> None: ...

    @abstractmethod
    def get_account_map(self, user_id: str) -> AccountMap: ...


class InstrumentRepository(ABC):
    @abstractmethod
    def ensure(self, instrument: Instrument) -> None: ...

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

    @abstractmethod
    def update_last_synced_at(
        self, instrument_id: str, last_synced_at: datetime
    ) -> None: ...


class TransactionRepository(ABC):
    @abstractmethod
    def add(self, transaction: Transaction) -> None: ...

    @abstractmethod
    def ensure(self, transaction: Transaction) -> None: ...

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

    @abstractmethod
    def get_distinct_dates(self, filter_: Filter | None = None) -> set[date]: ...

    @abstractmethod
    def get_distinct_instrument_ids(
        self, filter_: Filter | None = None
    ) -> set[str]: ...

    @abstractmethod
    def update(self, transaction: Transaction) -> None: ...

    @abstractmethod
    def remove(self, filter_: Filter) -> None: ...

    @abstractmethod
    def remove_by_id(self, transaction_id: str) -> None: ...

    @abstractmethod
    def remove_by_asset_account_id(self, account_id: str) -> None: ...

    @abstractmethod
    def exists(self, filter_: Filter) -> bool: ...

    @abstractmethod
    def exists_by_checksum(self, checksum: str) -> bool: ...


class FxRatesRepository(ABC):
    @abstractmethod
    def ensure(self, rates: FxRates) -> None: ...

    @abstractmethod
    def get_by_date(self, effective_on: date) -> FxRates | None: ...

    @abstractmethod
    def get_by_dates(self, dates: set[date]) -> list[FxRates]: ...

    @abstractmethod
    def get_latest(self) -> FxRates | None: ...

    @abstractmethod
    def get_distinct_dates(self) -> set[date]: ...

    def get_required_rates_by_date_map(self, dates: set[date]) -> dict[date, FxRates]:
        rates_list = self.get_by_dates(dates)
        rates_by_date = {rates.effective_on: rates for rates in rates_list}
        missing_dates = dates - rates_by_date.keys()

        if missing_dates:
            formatted_dates = ", ".join(
                missing_date.isoformat() for missing_date in sorted(missing_dates)
            )
            raise FxDataIntegrityError(
                detail=(
                    f"Missing historical FX rates for following dates {formatted_dates}."
                    "Please execute a FX rates data sync first."
                ),
            )

        return rates_by_date


class MarketDataRepository(ABC):
    @abstractmethod
    def ensure_stock_splits(self, splits: StockSplits) -> None: ...

    @abstractmethod
    def get_stock_splits_by_instrument_ids(
        self, instrument_ids: set[str]
    ) -> list[StockSplits]: ...
