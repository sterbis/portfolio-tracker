from datetime import date
from types import TracebackType
from typing import Protocol, Self

from filterutils import Filter

from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.account import AccountMap, AssetAccount
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.institution import Credentials, InstitutionConnection
from portfolio_tracker.domain.instrument import Instrument, InstrumentMetadata
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.domain.transaction import Transaction
from portfolio_tracker.domain.user import User


class UserReader(Protocol):
    def get_by_username(self, username: str) -> User | None: ...


class InstitutionConnectionReader(Protocol):
    def get_by_id(self, connection_id: str) -> InstitutionConnection | None: ...

    def get_by_ids(self, connection_ids: set[str]) -> list[InstitutionConnection]: ...

    def get_by_user_id(self, user_id: str) -> list[InstitutionConnection]: ...


class CredentialsReader(Protocol):
    def get(self, institution_connection_id: str) -> Credentials | None: ...

    def get_by_ids(self, institution_connection_ids: set[str]) -> list[Credentials]: ...


class AccountReader(Protocol):
    def get_by_id(self, account_id: str) -> AssetAccount | None: ...

    def get_by_external_id(
        self, institution_connection_id: str, external_id: str
    ) -> AssetAccount | None: ...

    def get_by_ids(self, account_ids: set[str]) -> list[AssetAccount]: ...

    def get_by_institution_connection_id(
        self, institution_connection_id: str
    ) -> list[AssetAccount]: ...

    def get_account_map(self, user_id: str) -> AccountMap: ...


class InstrumentReader(Protocol):
    def get(
        self,
        *,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Instrument]: ...

    def get_metadata(
        self,
        *,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[InstrumentMetadata]: ...

    def get_by_ids(self, instrument_ids: set[str]) -> list[Instrument]: ...

    def get_ids_by_symbols(self, symbols: set[str]) -> set[str]: ...


class TransactionReader(Protocol):
    def get(
        self,
        *,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Transaction]: ...

    def get_by_id(self, transaction_id: str) -> Transaction | None: ...

    def get_distinct_dates(self, filter_: Filter | None = None) -> set[date]: ...

    def get_distinct_instrument_ids(
        self, filter_: Filter | None = None
    ) -> set[str]: ...


class FxRatesReader(Protocol):
    def get_by_date(self, effective_on: date) -> FxRates | None: ...

    def get_by_dates(self, dates: set[date]) -> list[FxRates]: ...

    def get_latest(self) -> FxRates | None: ...

    def get_distinct_dates(self) -> set[date]: ...

    def get_missing_dates(
        self,
        required_dates: set[date],
        base_currency: Currency,
        quote_currencies: set[Currency],
    ) -> set[date]: ...

    def get_required_rates_by_date_map(
        self, dates: set[date]
    ) -> dict[date, FxRates]: ...


class MarketDataReader(Protocol):
    def get_stock_splits_by_instrument_ids(
        self, instrument_ids: set[str]
    ) -> list[StockSplits]: ...


class ReadOnlyUnitOfWork(Protocol):
    @property
    def accounts(self) -> AccountReader: ...

    @property
    def credentials(self) -> CredentialsReader: ...

    @property
    def fx_rates(self) -> FxRatesReader: ...

    @property
    def institution_connections(self) -> InstitutionConnectionReader: ...

    @property
    def instruments(self) -> InstrumentReader: ...

    @property
    def market_data(self) -> MarketDataReader: ...

    @property
    def transactions(self) -> TransactionReader: ...

    @property
    def users(self) -> UserReader: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class UserScopedAccountReader(Protocol):
    def get_by_id(self, account_id: str) -> AssetAccount: ...

    def get_by_external_id(
        self, institution_connection_id: str, external_id: str
    ) -> AssetAccount | None: ...

    def get_by_ids(self, account_ids: set[str]) -> list[AssetAccount]: ...

    def get_by_institution_connection_id(
        self, institution_connection_id: str
    ) -> list[AssetAccount]: ...


class UserScopedInstitutionConnectionReader(Protocol):
    def get_by_id(self, connection_id: str) -> InstitutionConnection: ...

    def get_by_ids(self, connection_ids: set[str]) -> list[InstitutionConnection]: ...

    def get_by_user_id(self, user_id: str) -> list[InstitutionConnection]: ...


class UserScopedTransactionReader(Protocol):
    def get(
        self,
        *,
        institution_connection_ids: set[str] | None = None,
        account_ids: set[str] | None = None,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Transaction]: ...

    def get_by_id(self, transaction_id: str) -> Transaction | None: ...

    def get_distinct_dates(
        self,
        institution_connection_ids: set[str] | None = None,
        account_ids: set[str] | None = None,
        filter_: Filter | None = None,
    ) -> set[date]: ...

    def get_distinct_instrument_ids(
        self,
        institution_connection_ids: set[str] | None = None,
        account_ids: set[str] | None = None,
        filter_: Filter | None = None,
    ) -> set[str]: ...


class UserScopedReadOnlyUnitOfWork(Protocol):
    @property
    def account_map(self) -> AccountMap: ...

    @property
    def accounts(self) -> UserScopedAccountReader: ...

    @property
    def credentials(self) -> CredentialsReader: ...

    @property
    def fx_rates(self) -> FxRatesReader: ...

    @property
    def institution_connections(self) -> UserScopedInstitutionConnectionReader: ...

    @property
    def instruments(self) -> InstrumentReader: ...

    @property
    def market_data(self) -> MarketDataReader: ...

    @property
    def transactions(self) -> UserScopedTransactionReader: ...

    @property
    def users(self) -> UserReader: ...
