from portfolio_tracker.domain.account import UserAccountsMap

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
    UserScopedTransactionRepository,
)


class UserScopedUnitOfWork:
    def __init__(
        self,
        uow: UnitOfWork,
        accounts_map: UserAccountsMap,
    ) -> None:
        self._uow = uow
        self.accounts_map = accounts_map
        self.accounts = UserScopedAccountRepository(
            self.accounts_map, self._uow.accounts
        )
        self.transactions = UserScopedTransactionRepository(
            self.accounts_map, self._uow.transactions
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
