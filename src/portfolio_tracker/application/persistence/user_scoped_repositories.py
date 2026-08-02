from abc import ABC
from datetime import date
from typing import Literal

from filterutils import Filter, FilterNode, FilterTree, Operator

from portfolio_tracker.application.shared.exceptions import (
    AssetAccountNotFoundError,
    InstitutionAccountNotFoundError,
)
from portfolio_tracker.domain.account import (
    AssetAccount,
    InstitutionAccount,
    UserAccountsMap,
)
from portfolio_tracker.domain.transaction import Transaction

from .repositories import (
    AccountRepository,
    TransactionRepository,
)


class UserScopedRepository(ABC):
    def __init__(
        self,
        accounts_map: UserAccountsMap,
    ) -> None:
        self._accounts_map = accounts_map

    def _verify_institution_account_ownership(self, account_id: str) -> None:
        if account_id not in self._accounts_map.institution_account_ids:
            raise InstitutionAccountNotFoundError(account_id)

    def _verify_institution_accounts_ownership(self, account_ids: set[str]) -> None:
        if (
            not_owned_account_ids := account_ids
            - self._accounts_map.institution_account_ids
        ):
            raise InstitutionAccountNotFoundError(not_owned_account_ids)

    def _verify_asset_account_ownership(self, account_id: str) -> None:
        if account_id not in self._accounts_map.all_asset_account_ids:
            raise AssetAccountNotFoundError(account_id)

    def _verify_asset_accounts_ownership(self, account_ids: set[str]) -> None:
        if (
            not_owned_account_ids := account_ids
            - self._accounts_map.all_asset_account_ids
        ):
            raise AssetAccountNotFoundError(not_owned_account_ids)


class UserScopedAccountRepository(UserScopedRepository):
    def __init__(
        self,
        accounts_map: UserAccountsMap,
        account_repository: AccountRepository,
    ) -> None:
        super().__init__(accounts_map)
        self._account_repository = account_repository

    def add_institution_account(self, account: InstitutionAccount) -> None:
        self._account_repository.add_institution_account(account)

    def get_institution_account_by_id(self, account_id: str) -> InstitutionAccount:
        self._verify_institution_account_ownership(account_id)
        institution_account = self._account_repository.get_institution_account_by_id(
            account_id
        )

        if not institution_account:
            raise RuntimeError(
                f"Institution account {account_id} must exist after ownership verification."
            )

        return institution_account

    def get_institution_accounts_by_ids(
        self, account_ids: set[str]
    ) -> list[InstitutionAccount]:
        self._verify_institution_accounts_ownership(account_ids)
        return self._account_repository.get_institution_accounts_by_ids(account_ids)

    def get_institution_accounts_by_user_id(
        self, user_id: str
    ) -> list[InstitutionAccount]:
        return self._account_repository.get_institution_accounts_by_user_id(user_id)

    def update_institution_account(self, account: InstitutionAccount) -> None:
        return self._account_repository.update_institution_account(account)

    def remove_institution_account_by_id(self, account_id: str) -> None:
        self._verify_institution_account_ownership(account_id)
        return self._account_repository.remove_institution_account_by_id(account_id)

    def ensure_asset_account(self, account: AssetAccount) -> None:
        return self._account_repository.ensure_asset_account(account)

    def get_asset_account_by_id(self, account_id: str) -> AssetAccount:
        self._verify_asset_account_ownership(account_id)
        asset_account = self._account_repository.get_asset_account_by_id(account_id)

        if not asset_account:
            raise RuntimeError(
                f"Asset account {account_id} must exist after ownership verification."
            )

        return asset_account

    def get_asset_account_by_external_id(
        self, institution_account_id: str, external_id: str
    ) -> AssetAccount | None:
        self._verify_institution_account_ownership(institution_account_id)
        return self._account_repository.get_asset_account_by_external_id(
            institution_account_id, external_id
        )

    def get_asset_accounts_by_ids(self, account_ids: set[str]) -> list[AssetAccount]:
        self._verify_asset_accounts_ownership(account_ids)
        return self._account_repository.get_asset_accounts_by_ids(account_ids)

    def get_asset_accounts_by_institution_account_id(
        self, institution_account_id: str
    ) -> list[AssetAccount]:
        self._verify_institution_account_ownership(institution_account_id)
        return self._account_repository.get_asset_accounts_by_institution_account_id(
            institution_account_id
        )

    def update_asset_account(self, account: AssetAccount) -> None:
        return self._account_repository.update_asset_account(account)


class UserScopedTransactionRepository(UserScopedRepository):
    def __init__(
        self,
        accounts_map: UserAccountsMap,
        transaction_repository: TransactionRepository,
    ) -> None:
        super().__init__(accounts_map)
        self._transaction_repository = transaction_repository

    def add(self, transaction: Transaction) -> None:
        self._verify_asset_account_ownership(transaction.asset_account_id)
        return self._transaction_repository.add(transaction)

    def ensure(self, transaction: Transaction) -> None:
        self._verify_asset_account_ownership(transaction.asset_account_id)
        return self._transaction_repository.ensure(transaction)

    def get(
        self,
        *,
        institution_account_ids: set[str] | None = None,
        asset_account_ids: set[str] | None = None,
        filter_: Filter | None = None,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Transaction]:
        return self._transaction_repository.get(
            filter_=self._get_user_scoped_filter(
                institution_account_ids=institution_account_ids,
                asset_account_ids=asset_account_ids,
                filter_=filter_,
            ),
            order_by=order_by,
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
        institution_account_ids: set[str] | None = None,
        asset_account_ids: set[str] | None = None,
        filter_: Filter | None = None
    ) -> set[date]:
        return self._transaction_repository.get_distinct_dates(
            filter_=self._get_user_scoped_filter(
                institution_account_ids=institution_account_ids,
                asset_account_ids=asset_account_ids,
                filter_=filter_,
            ),
        )

    def get_distinct_instrument_ids(
        self,
        institution_account_ids: set[str] | None = None,
        asset_account_ids: set[str] | None = None,
        filter_: Filter | None = None
    ) -> set[str]:
        return self._transaction_repository.get_distinct_instrument_ids(
            filter_=self._get_user_scoped_filter(
                institution_account_ids=institution_account_ids,
                asset_account_ids=asset_account_ids,
                filter_=filter_,
            )
        )

    def update(self, transaction: Transaction) -> None:
        self._verify_asset_account_ownership(transaction.asset_account_id)
        return self._transaction_repository.update(transaction)

    def remove(self, transaction: Transaction) -> None:
        self._verify_asset_account_ownership(transaction.asset_account_id)
        return self._transaction_repository.remove_by_id(transaction.id)

    def remove_by_id(self, transaction_id: str) -> None:
        return self._transaction_repository.remove(
            filter_=self._get_user_scoped_filter(transaction_id=transaction_id)
        )

    def remove_by_asset_account_id(self, account_id: str) -> None:
        self._verify_asset_account_ownership(account_id)
        return self._transaction_repository.remove_by_asset_account_id(account_id)

    def exists(self, transaction: Transaction) -> bool:
        self._verify_asset_account_ownership(transaction.asset_account_id)
        return self._transaction_repository.exists_by_checksum(transaction.checksum)

    def _get_user_scoped_filter(
        self,
        *,
        institution_account_ids: set[str] | None = None,
        asset_account_ids: set[str] | None = None,
        transaction_id: str | None = None,
        checksum: str | None = None,
        filter_: Filter | None = None,
    ) -> FilterTree:
        if institution_account_ids:
            self._verify_institution_accounts_ownership(institution_account_ids)

        if asset_account_ids:
            self._verify_asset_accounts_ownership(asset_account_ids)

        asset_account_ids = self._accounts_map.resolve_asset_account_ids(
            institution_account_ids, asset_account_ids
        )

        scoped_filter = FilterTree()

        scoped_filter.add_child(
            FilterNode("asset_account_id", Operator.IN, asset_account_ids, Transaction)
        )
        if transaction_id:
            scoped_filter.add_child(
                FilterNode("transaction_id", Operator.EQ, transaction_id, Transaction)
            )
        if checksum:
            scoped_filter.add_child(
                FilterNode("checksum", Operator.EQ, checksum, Transaction)
            )
        if filter_:
            scoped_filter.add_child(filter_)

        return scoped_filter
