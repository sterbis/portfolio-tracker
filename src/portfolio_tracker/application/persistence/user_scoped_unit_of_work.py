from portfolio_tracker.domain.account import AccountMap

from .read_only import (
    CredentialsReader,
    FxRatesReader,
    InstrumentReader,
    MarketDataReader,
    ReadOnlyUnitOfWork,
    UserReader,
)
from .repositories import (
    CredentialsRepository,
    FxRatesRepository,
    InstrumentRepository,
    MarketDataRepository,
    UserRepository,
)
from .unit_of_work import UnitOfWork
from .user_scoped_repositories import (
    UserScopedAccountReaderRepository,
    UserScopedAccountRepository,
    UserScopedInstitutionConnectionReaderRepository,
    UserScopedInstitutionConnectionRepository,
    UserScopedTransactionReaderRepository,
    UserScopedTransactionRepository,
)


class UserScopedUnitOfWork:
    def __init__(
        self,
        uow: UnitOfWork,
        account_map: AccountMap,
    ) -> None:
        self._uow = uow
        self.account_map = account_map
        self.accounts = UserScopedAccountRepository(
            self.account_map, self._uow.accounts
        )
        self.institution_connections = UserScopedInstitutionConnectionRepository(
            self.account_map, self._uow.institution_connections
        )
        self.transactions = UserScopedTransactionRepository(
            self.account_map, self._uow.transactions
        )

    @property
    def credentials(self) -> CredentialsRepository:
        return self._uow.credentials

    @property
    def fx_rates(self) -> FxRatesRepository:
        return self._uow.fx_rates

    @property
    def instruments(self) -> InstrumentRepository:
        return self._uow.instruments

    @property
    def market_data(self) -> MarketDataRepository:
        return self._uow.market_data

    @property
    def users(self) -> UserRepository:
        return self._uow.users

    def commit(self) -> None:
        self._uow.commit()

    def rollback(self) -> None:
        self._uow.rollback()


class UserScopedReadOnlyUnitOfWork:
    def __init__(
        self,
        uow: ReadOnlyUnitOfWork,
        account_map: AccountMap,
    ) -> None:
        self.account_map = account_map
        self.accounts = UserScopedAccountReaderRepository(account_map, uow.accounts)
        self.institution_connections = UserScopedInstitutionConnectionReaderRepository(
            account_map, uow.institution_connections
        )
        self.transactions = UserScopedTransactionReaderRepository(
            account_map, uow.transactions
        )
        self._uow = uow

    @property
    def credentials(self) -> CredentialsReader:
        return self._uow.credentials

    @property
    def fx_rates(self) -> FxRatesReader:
        return self._uow.fx_rates

    @property
    def instruments(self) -> InstrumentReader:
        return self._uow.instruments

    @property
    def market_data(self) -> MarketDataReader:
        return self._uow.market_data

    @property
    def users(self) -> UserReader:
        return self._uow.users
