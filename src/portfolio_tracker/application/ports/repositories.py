from abc import ABC, abstractmethod
from datetime import date
from typing import Literal

from filterutils import Filter

from portfolio_tracker.domain.accounts import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.instruments import Instrument
from portfolio_tracker.domain.ledger import Transaction
from portfolio_tracker.domain.market_data import FxRates, StockSplits
from portfolio_tracker.domain.user import User


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> None: ...

    @abstractmethod
    def get_by_username(self, username: str) -> User | None: ...


class AccountRepository(ABC):
    @abstractmethod
    def add_institution_account(self, account: InstitutionAccount) -> None: ...

    @abstractmethod
    def get_institution_account_by_id(
        self, account_id: str
    ) -> InstitutionAccount | None: ...

    @abstractmethod
    def get_institution_accounts_by_ids(
        self, account_ids: set[str]
    ) -> list[InstitutionAccount]: ...

    @abstractmethod
    def get_institution_account_id_by_asset_account_id_map(
        self, asset_account_ids: set[str]
    ) -> dict[str, str]: ...

    @abstractmethod
    def update_institution_account(self, account: InstitutionAccount) -> None: ...

    @abstractmethod
    def remove_institution_account_by_id(self, account_id: str) -> None: ...

    @abstractmethod
    def add_asset_account(self, account: AssetAccount) -> None: ...

    @abstractmethod
    def get_asset_accounts_by_ids(
        self, account_ids: set[str]
    ) -> list[AssetAccount]: ...

    @abstractmethod
    def get_asset_account_by_external_id(
        self, institution_account_id: str, external_id: str
    ) -> AssetAccount | None: ...


class InstrumentRepository(ABC):
    @abstractmethod
    def ensure(self, instrument: Instrument) -> None: ...

    @abstractmethod
    def get(
        self,
        *,
        filter_: Filter | None = None,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Instrument]: ...

    @abstractmethod
    def get_by_ids(self, instrument_ids: set[str]) -> list[Instrument]: ...


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
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
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
    def remove_by_id(self, transaction_id: str) -> None: ...

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
                f"Data Integrity Violation: Missing historical FX rates for "
                f"following dates {formatted_dates}. "
                "Please execute a FX rates data sync first."
            )

        return rates_by_date


class MarketDataRepository(ABC):
    @abstractmethod
    def ensure_stock_splits(self, splits: StockSplits) -> None: ...

    @abstractmethod
    def get_stock_splits_by_instrument_ids(
        self, instrument_ids: set[str]
    ) -> list[StockSplits]: ...


class FxDataIntegrityError(Exception):
    pass
