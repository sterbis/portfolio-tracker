from abc import ABC
from datetime import date

from filterutils import Filter, FilterNode, FilterTree, Operator

from portfolio_tracker.application.shared.errors import (
    AssetAccountNotFoundError,
    InstitutionConnectionNotFoundError,
)
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.account import (
    AccountMap,
    AssetAccount,
)
from portfolio_tracker.domain.institution import InstitutionConnection
from portfolio_tracker.domain.transaction import Transaction

from .repositories import (
    AccountRepository,
    InstitutionConnectionRepository,
    TransactionRepository,
)


class UserScopedRepository(ABC):
    def __init__(
        self,
        account_map: AccountMap,
    ) -> None:
        self._account_map = account_map

    def _verify_institution_connection_ownership(
        self, connection_id: str | set[str]
    ) -> None:
        if (
            isinstance(connection_id, str)
            and connection_id not in self._account_map.institution_connection_ids
        ):
            raise InstitutionConnectionNotFoundError(connection_id)

        if isinstance(connection_id, set) and (
            not_owned_connection_ids := connection_id
            - self._account_map.institution_connection_ids
        ):
            raise InstitutionConnectionNotFoundError(not_owned_connection_ids)

    def _verify_asset_account_ownership(self, account_id: str | set[str]) -> None:
        if (
            isinstance(account_id, str)
            and account_id not in self._account_map.account_ids
        ):
            raise AssetAccountNotFoundError(account_id)

        if isinstance(account_id, set) and (
            not_owned_account_ids := account_id - self._account_map.account_ids
        ):
            raise AssetAccountNotFoundError(not_owned_account_ids)


class UserScopedInstitutionConnectionRepository(UserScopedRepository):
    def __init__(
        self,
        accounts_map: AccountMap,
        connection_repository: InstitutionConnectionRepository,
    ) -> None:
        super().__init__(accounts_map)
        self._connection_repository = connection_repository

    def add(self, account: InstitutionConnection) -> None:
        self._connection_repository.add(account)

    def get_by_id(self, connection_id: str) -> InstitutionConnection:
        self._verify_institution_connection_ownership(connection_id)
        connection = self._connection_repository.get_by_id(connection_id)

        if not connection:
            raise RuntimeError(
                f"Institution connection {connection_id} must exist after ownership verification."
            )

        return connection

    def get_by_ids(self, connection_ids: set[str]) -> list[InstitutionConnection]:
        self._verify_institution_connection_ownership(connection_ids)
        return self._connection_repository.get_by_ids(connection_ids)

    def get_by_user_id(self, user_id: str) -> list[InstitutionConnection]:
        return self._connection_repository.get_by_user_id(user_id)

    def update(self, connection: InstitutionConnection) -> None:
        return self._connection_repository.update(connection)

    def remove_by_id(self, connection_id: str) -> None:
        self._verify_institution_connection_ownership(connection_id)
        return self._connection_repository.remove_by_id(connection_id)


class UserScopedAccountRepository(UserScopedRepository):
    def __init__(
        self,
        account_map: AccountMap,
        account_repository: AccountRepository,
    ) -> None:
        super().__init__(account_map)
        self._account_repository = account_repository

    def ensure(self, account: AssetAccount) -> None:
        return self._account_repository.ensure(account)

    def get_by_id(self, account_id: str) -> AssetAccount:
        self._verify_asset_account_ownership(account_id)
        account = self._account_repository.get_by_id(account_id)

        if not account:
            raise RuntimeError(
                f"Asset account {account_id} must exist after ownership verification."
            )

        return account

    def get_by_external_id(
        self, institution_connection_id: str, external_id: str
    ) -> AssetAccount | None:
        self._verify_institution_connection_ownership(institution_connection_id)
        return self._account_repository.get_by_external_id(
            institution_connection_id, external_id
        )

    def get_by_ids(self, account_ids: set[str]) -> list[AssetAccount]:
        self._verify_asset_account_ownership(account_ids)
        return self._account_repository.get_by_ids(account_ids)

    def get_by_institution_connection_id(
        self, institution_connection_id: str
    ) -> list[AssetAccount]:
        self._verify_institution_connection_ownership(institution_connection_id)
        return self._account_repository.get_by_institution_connection_id(
            institution_connection_id
        )

    def update(self, account: AssetAccount) -> None:
        return self._account_repository.update(account)


class UserScopedTransactionRepository(UserScopedRepository):
    def __init__(
        self,
        account_map: AccountMap,
        transaction_repository: TransactionRepository,
    ) -> None:
        super().__init__(account_map)
        self._transaction_repository = transaction_repository

    def add(self, transaction: Transaction) -> None:
        self._verify_asset_account_ownership(transaction.account_id)
        return self._transaction_repository.add(transaction)

    def ensure(self, transaction: Transaction) -> None:
        self._verify_asset_account_ownership(transaction.account_id)
        return self._transaction_repository.ensure(transaction)

    def get(
        self,
        *,
        institution_connection_ids: set[str] | None = None,
        account_ids: set[str] | None = None,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Transaction]:
        filter_ = self._get_user_scoped_filter(
            institution_connection_ids=institution_connection_ids,
            asset_account_ids=account_ids,
            filter_=filter_,
        )

        return self._transaction_repository.get(
            filter_=filter_,
            sorts=sorts,
            limit=limit,
            offset=offset,
        )

    def get_by_id(self, transaction_id: str) -> Transaction | None:
        transactions = self._transaction_repository.get(
            filter_=self._get_user_scoped_filter(transaction_id=transaction_id),
        )
        if not transactions:
            return None

        return transactions[0]

    def get_distinct_dates(
        self,
        institution_connection_ids: set[str] | None = None,
        account_ids: set[str] | None = None,
        filter_: Filter | None = None,
    ) -> set[date]:
        return self._transaction_repository.get_distinct_dates(
            filter_=self._get_user_scoped_filter(
                institution_connection_ids=institution_connection_ids,
                asset_account_ids=account_ids,
                filter_=filter_,
            ),
        )

    def get_distinct_instrument_ids(
        self,
        institution_connection_ids: set[str] | None = None,
        account_ids: set[str] | None = None,
        filter_: Filter | None = None,
    ) -> set[str]:
        return self._transaction_repository.get_distinct_instrument_ids(
            filter_=self._get_user_scoped_filter(
                institution_connection_ids=institution_connection_ids,
                asset_account_ids=account_ids,
                filter_=filter_,
            )
        )

    def update(self, transaction: Transaction) -> None:
        self._verify_asset_account_ownership(transaction.account_id)
        return self._transaction_repository.update(transaction)

    def remove(self, transaction: Transaction) -> None:
        self._verify_asset_account_ownership(transaction.account_id)
        return self._transaction_repository.remove_by_id(transaction.id)

    def remove_by_id(self, transaction_id: str) -> None:
        return self._transaction_repository.remove(
            filter_=self._get_user_scoped_filter(transaction_id=transaction_id)
        )

    def remove_by_asset_account_id(self, account_id: str) -> None:
        self._verify_asset_account_ownership(account_id)
        return self._transaction_repository.remove_by_asset_account_id(account_id)

    def exists(self, transaction: Transaction) -> bool:
        self._verify_asset_account_ownership(transaction.account_id)
        return self._transaction_repository.exists_by_checksum(transaction.checksum)

    def _get_user_scoped_filter(
        self,
        *,
        institution_connection_ids: set[str] | None = None,
        asset_account_ids: set[str] | None = None,
        transaction_id: str | None = None,
        checksum: str | None = None,
        filter_: Filter | None = None,
    ) -> FilterTree:
        if institution_connection_ids:
            self._verify_institution_connection_ownership(institution_connection_ids)

        if asset_account_ids:
            self._verify_asset_account_ownership(asset_account_ids)

        asset_account_ids = self._account_map.resolve_account_ids(
            institution_connection_ids, asset_account_ids
        )

        scoped_filter = FilterTree()

        scoped_filter.add_child(
            FilterNode("asset_account_id", Operator.IN, asset_account_ids, Transaction)
        )
        if transaction_id:
            scoped_filter.add_child(
                FilterNode("id", Operator.EQ, transaction_id, Transaction)
            )
        if checksum:
            scoped_filter.add_child(
                FilterNode("checksum", Operator.EQ, checksum, Transaction)
            )
        if filter_:
            scoped_filter.add_child(filter_)

        return scoped_filter
