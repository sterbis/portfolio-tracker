import sqlite3
from typing import Any, Literal

from filterutils import Filter, FilterNode, FilterTree, Operator

from portfolio_tracker.application.persistence import AccountRepository
from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount

from ..executor import SqliteExecutor


class SqliteAccountRepository(AccountRepository):
    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def add_institution_account(self, account: InstitutionAccount) -> None:
        self._executor.insert(
            table="institution_account",
            values=self._institution_account_to_values(account),
        )

    def get_institution_accounts(
        self,
        *,
        filter_: Filter | None = None,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[InstitutionAccount]:
        rows = self._executor.select(
            table="institution_account",
            filter_=filter_,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_institution_account(row) for row in rows]

    def get_institution_account_by_id(
        self, account_id: str
    ) -> InstitutionAccount | None:
        row = self._executor.select_one(
            table="institution_account",
            filter_=FilterNode("institution_account_id", Operator.EQ, account_id),
        )
        return self._row_to_institution_account(row) if row else None

    def get_institution_accounts_by_ids(
        self, account_ids: set[str]
    ) -> list[InstitutionAccount]:
        return self.get_institution_accounts(
            filter_=FilterNode("institution_account_id", Operator.IN, account_ids)
        )

    def get_institution_accounts_by_user_id(
        self, user_id: str
    ) -> list[InstitutionAccount]:
        return self.get_institution_accounts(
            filter_=FilterNode("user_id", Operator.EQ, user_id)
        )

    def get_institution_account_id_by_asset_account_id_map(
        self, asset_account_ids: set[str]
    ) -> dict[str, str]:
        rows = self._executor.select(
            table="asset_account",
            columns=["asset_account_id", "institution_account_id"],
            filter_=FilterNode("asset_account_id", Operator.IN, asset_account_ids),
        )
        return {row["asset_account_id"]: row["institution_account_id"] for row in rows}

    def update_institution_account(self, account: InstitutionAccount) -> None:
        self._executor.update(
            table="institution_account",
            values=self._institution_account_to_values(account),
            filter_=FilterNode("institution_account_id", Operator.EQ, account.id),
        )

    def remove_institution_account_by_id(self, account_id: str) -> None:
        self._executor.delete(
            table="institution_account",
            filter_=FilterNode("institution_account_id", Operator.EQ, account_id),
        )

    def add_asset_account(self, account: AssetAccount) -> None:
        self._executor.insert(
            table="asset_account",
            values=self._asset_account_to_values(account),
        )

    def get_asset_accounts(
        self,
        *,
        filter_: Filter | None = None,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[AssetAccount]:
        rows = self._executor.select(
            table="asset_account",
            filter_=filter_,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_asset_account(row) for row in rows]

    def get_asset_account_by_id(self, account_id: str) -> AssetAccount | None:
        row = self._executor.select_one(
            table="asset_account",
            filter_=FilterNode("asset_account_id", Operator.EQ, account_id),
        )
        return self._row_to_asset_account(row) if row else None

    def get_asset_account_by_external_id(
        self, institution_account_id: str, external_id: str
    ) -> AssetAccount | None:
        filter_ = FilterTree()
        filter_.add_child(
            FilterNode("institution_account_id", Operator.EQ, institution_account_id)
        )
        filter_.add_child(FilterNode("external_id", Operator.EQ, external_id))
        row = self._executor.select_one(
            table="asset_account",
            filter_=filter_,
        )
        return self._row_to_asset_account(row) if row else None

    def get_asset_accounts_by_ids(self, account_ids: set[str]) -> list[AssetAccount]:
        return self.get_asset_accounts(
            filter_=FilterNode("asset_account_id", Operator.IN, account_ids)
        )

    def get_asset_accounts_by_institution_account_id(
        self, institution_account_id: str
    ) -> list[AssetAccount]:
        return self.get_asset_accounts(
            filter_=FilterNode(
                "institution_account_id", Operator.EQ, institution_account_id
            )
        )

    def get_asset_accounts_by_user_id(self, user_id: str) -> list[AssetAccount]:
        institution_accounts = self.get_institution_accounts_by_user_id(user_id)
        return self.get_asset_accounts(
            filter_=FilterNode(
                "institution_account_id",
                Operator.IN,
                {
                    institution_account.id
                    for institution_account in institution_accounts
                },
            )
        )

    def get_deactivated_asset_account_external_ids(
        self, institution_account_id: str
    ) -> set[str]:
        filter_ = FilterTree()
        filter_.add_child(
            FilterNode("institution_account_id", Operator.EQ, institution_account_id)
        )
        filter_.add_child(FilterNode("is_active", Operator.EQ, False))
        rows = self._executor.select(
            table="asset_account",
            columns=["external_id"],
            filter_=filter_,
        )
        return {row["external_id"] for row in rows}

    def update_asset_account(self, account: AssetAccount) -> None:
        self._executor.update(
            table="asset_account",
            values=self._asset_account_to_values(account),
            filter_=FilterNode("asset_account_id", Operator.EQ, account.id),
        )

    def remove_asset_account_by_id(self, account_id: str) -> None:
        self._executor.delete(
            table="asset_account",
            filter_=FilterNode("asset_account_id", Operator.EQ, account_id),
        )

    def _institution_account_to_values(
        self, account: InstitutionAccount
    ) -> dict[str, Any]:
        return {
            "institution_account_id": account.id,
            "institution_id": account.institution_id,
            "user_id": account.user_id,
            "name": account.name,
            "created_on": account.created_on,
            "last_synced_at": account.last_synced_at,
        }

    def _asset_account_to_values(self, account: AssetAccount) -> dict[str, Any]:
        return {
            "asset_account_id": account.id,
            "external_id": account.external_id,
            "institution_account_id": account.institution_account_id,
            "name": account.name,
            "is_active": account.is_active,
        }

    def _row_to_institution_account(self, row: sqlite3.Row) -> InstitutionAccount:
        return InstitutionAccount(
            id=row["institution_account_id"],
            user_id=row["user_id"],
            institution_id=row["institution_id"],
            name=row["name"],
            created_on=row["created_on"],
            last_synced_at=row["last_synced_at"],
        )

    def _row_to_asset_account(self, row: sqlite3.Row) -> AssetAccount:
        return AssetAccount(
            id=row["asset_account_id"],
            external_id=row["external_id"],
            institution_account_id=row["institution_account_id"],
            name=row["name"],
            is_active=bool(row["is_active"]),
        )
