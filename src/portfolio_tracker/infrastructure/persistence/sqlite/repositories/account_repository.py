from typing import Any

from filterutils import Filter, FilterNode, FilterTree, Operator

from portfolio_tracker.application.persistence import AccountRepository
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.account import (
    AccountMap,
    AssetAccount,
)
from portfolio_tracker.domain.institution import InstitutionConnection
from portfolio_tracker.infrastructure.persistence.sqlite.executor import SqliteExecutor
from portfolio_tracker.infrastructure.persistence.sqlite.registry import FieldReference


class SqliteAccountRepository(AccountRepository):
    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def ensure(self, account: AssetAccount) -> None:
        self._executor.insert_on_conflict_do_nothing(
            model=AssetAccount,
            values=self._asset_account_to_values(account),
            conflict_field_names=["id"],
        )

    def get(
        self,
        *,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[AssetAccount]:
        rows = self._executor.select(
            model=AssetAccount,
            filter_=filter_,
            sorts=sorts,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_asset_account(row) for row in rows]

    def get_by_id(self, account_id: str) -> AssetAccount | None:
        row = self._executor.select_one(
            model=AssetAccount,
            filter_=FilterNode("id", Operator.EQ, account_id, AssetAccount),
        )
        return self._row_to_asset_account(row) if row else None

    def get_by_external_id(
        self, institution_connection_id: str, external_id: str
    ) -> AssetAccount | None:
        filter_ = FilterTree()
        filter_.add_child(
            FilterNode(
                "institution_connection_id",
                Operator.EQ,
                institution_connection_id,
                AssetAccount,
            )
        )
        filter_.add_child(
            FilterNode("external_id", Operator.EQ, external_id, AssetAccount)
        )
        row = self._executor.select_one(
            model=AssetAccount,
            filter_=filter_,
        )
        return self._row_to_asset_account(row) if row else None

    def get_by_ids(self, account_ids: set[str]) -> list[AssetAccount]:
        if not account_ids:
            return []

        return self.get(
            filter_=FilterNode("id", Operator.IN, account_ids, AssetAccount)
        )

    def get_by_institution_connection_id(
        self, institution_connection_id: str
    ) -> list[AssetAccount]:
        return self.get(
            filter_=FilterNode(
                "institution_connection_id",
                Operator.EQ,
                institution_connection_id,
                AssetAccount,
            )
        )

    def update(self, account: AssetAccount) -> None:
        self._executor.update(
            model=AssetAccount,
            values=self._asset_account_to_values(account),
            filter_=FilterNode("id", Operator.EQ, account.id, AssetAccount),
        )

    def get_account_map(self, user_id: str) -> AccountMap:
        fields = [
            FieldReference(AssetAccount, "institution_connection_id"),
            FieldReference(AssetAccount, "id"),
            FieldReference(AssetAccount, "external_id"),
            FieldReference(AssetAccount, "is_active"),
        ]

        rows = self._executor.select(
            model=AssetAccount,
            fields=fields,
            filter_=FilterNode("user_id", Operator.EQ, user_id, InstitutionConnection),
        )

        institution_connection_ids: set[str] = set()
        account_id_to_institution_connection_id: dict[str, str] = {}
        account_id_to_account_external_id: dict[str, str] = {}
        deactivated_account_ids: set[str] = set()

        for row in rows:
            (
                institution_connection_id,
                account_id,
                account_external_id,
                is_active,
            ) = row.unpack(*fields)

            institution_connection_ids.add(institution_connection_id)
            account_id_to_institution_connection_id[account_id] = (
                institution_connection_id
            )
            account_id_to_account_external_id[account_id] = account_external_id
            if not is_active:
                deactivated_account_ids.add(account_id)

        return AccountMap(
            user_id=user_id,
            institution_connection_ids=institution_connection_ids,
            account_id_to_institution_connection_id=account_id_to_institution_connection_id,
            account_id_to_account_external_id=account_id_to_account_external_id,
            deactivated_account_ids=deactivated_account_ids,
        )

    def _asset_account_to_values(self, account: AssetAccount) -> dict[str, Any]:
        return {
            "id": account.id,
            "external_id": account.external_id,
            "institution_connection_id": account.institution_connection_id,
            "name": account.name,
            "is_active": account.is_active,
        }

    def _row_to_asset_account(self, row: dict[FieldReference, Any]) -> AssetAccount:
        def field(field: str) -> FieldReference:
            return FieldReference(AssetAccount, field)

        return AssetAccount(
            id=row[field("id")],
            external_id=row[field("external_id")],
            institution_connection_id=row[field("institution_connection_id")],
            name=row[field("name")],
            is_active=bool(row[field("is_active")]),
        )
