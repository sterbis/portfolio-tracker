from portfolio_tracker.domain.account import AccountMap

from .repositories import (
    CredentialsRepository,
    FxRatesRepository,
    InstrumentRepository,
    MarketDataRepository,
    UserRepository,
)
from .unit_of_work import UnitOfWork
from .user_scoped_repositories import (
    UserScopedAccountRepository,
    UserScopedInstitutionConnectionRepository,
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
