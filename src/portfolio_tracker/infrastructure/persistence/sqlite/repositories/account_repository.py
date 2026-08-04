from typing import Any

from filterutils import Filter, FilterNode, FilterTree, Operator

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import AccountRepository, OrderBy
from portfolio_tracker.domain.account import UserAccountsMap, AssetAccount, InstitutionAccount

from portfolio_tracker.infrastructure.persistence.sqlite.executor import SqliteExecutor
from portfolio_tracker.infrastructure.persistence.sqlite.registry import FieldReference


class SqliteAccountRepository(AccountRepository):
    def __init__(
        self, institution_registry: InstitutionRegistry, executor: SqliteExecutor
    ) -> None:
        self._institution_registry = institution_registry
        self._executor = executor

    def add_institution_account(self, account: InstitutionAccount) -> None:
        self._executor.insert(
            entity=InstitutionAccount,
            values=self._institution_account_to_values(account),
        )

    def get_institution_accounts(
        self,
        *,
        filter_: Filter | None = None,
        order_by_list: list[OrderBy] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[InstitutionAccount]:
        rows = self._executor.select(
            entity=InstitutionAccount,
            filter_=filter_,
            order_by_list=order_by_list,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_institution_account(row) for row in rows]

    def get_institution_account_by_id(
        self, account_id: str
    ) -> InstitutionAccount | None:
        row = self._executor.select_one(
            entity=InstitutionAccount,
            filter_=FilterNode("id", Operator.EQ, account_id, InstitutionAccount),
        )
        return self._row_to_institution_account(row) if row else None

    def get_institution_accounts_by_ids(
        self, account_ids: set[str]
    ) -> list[InstitutionAccount]:
        if not account_ids:
            return []

        return self.get_institution_accounts(
            filter_=FilterNode("id", Operator.IN, account_ids, InstitutionAccount)
        )

    def get_institution_accounts_by_user_id(
        self, user_id: str
    ) -> list[InstitutionAccount]:
        return self.get_institution_accounts(
            filter_=FilterNode("user_id", Operator.EQ, user_id, InstitutionAccount)
        )

    def update_institution_account(self, account: InstitutionAccount) -> None:
        self._executor.update(
            entity=InstitutionAccount,
            values=self._institution_account_to_values(account),
            filter_=FilterNode("id", Operator.EQ, account.id, InstitutionAccount),
        )

    def remove_institution_account_by_id(self, account_id: str) -> None:
        self._executor.delete(
            entity=InstitutionAccount,
            filter_=FilterNode("id", Operator.EQ, account_id, InstitutionAccount),
        )

    def ensure_asset_account(self, account: AssetAccount) -> None:
        self._executor.insert_on_conflict_do_nothing(
            entity=AssetAccount,
            values=self._asset_account_to_values(account),
            conflict_field_names=["institution_account_id", "external_id"],
        )

    def get_asset_accounts(
        self,
        *,
        filter_: Filter | None = None,
        order_by_list: list[OrderBy] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[AssetAccount]:
        rows = self._executor.select(
            entity=AssetAccount,
            filter_=filter_,
            order_by_list=order_by_list,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_asset_account(row) for row in rows]

    def get_asset_account_by_id(self, account_id: str) -> AssetAccount | None:
        row = self._executor.select_one(
            entity=AssetAccount,
            filter_=FilterNode("id", Operator.EQ, account_id, AssetAccount),
        )
        return self._row_to_asset_account(row) if row else None

    def get_asset_account_by_external_id(
        self, institution_account_id: str, external_id: str
    ) -> AssetAccount | None:
        filter_ = FilterTree()
        filter_.add_child(
            FilterNode("institution_account_id", Operator.EQ, institution_account_id, AssetAccount)
        )
        filter_.add_child(FilterNode("external_id", Operator.EQ, external_id, AssetAccount))
        row = self._executor.select_one(
            entity=AssetAccount,
            filter_=filter_,
        )
        return self._row_to_asset_account(row) if row else None

    def get_asset_accounts_by_ids(self, account_ids: set[str]) -> list[AssetAccount]:
        if not account_ids:
            return []

        return self.get_asset_accounts(
            filter_=FilterNode("id", Operator.IN, account_ids, AssetAccount)
        )

    def get_asset_accounts_by_institution_account_id(
        self, institution_account_id: str
    ) -> list[AssetAccount]:
        return self.get_asset_accounts(
            filter_=FilterNode(
                "institution_account_id", Operator.EQ, institution_account_id, AssetAccount
            )
        )

    def update_asset_account(self, account: AssetAccount) -> None:
        self._executor.update(
            entity=AssetAccount,
            values=self._asset_account_to_values(account),
            filter_=FilterNode("id", Operator.EQ, account.id, AssetAccount),
        )

    def get_user_accounts_map(self, user_id: str) -> UserAccountsMap:
        references = [
            FieldReference("institution_account_id", AssetAccount),
            FieldReference("id", AssetAccount),
            FieldReference("external_id", AssetAccount),
            FieldReference("is_active", AssetAccount),
        ]

        rows = self._executor.select(
            entity=AssetAccount,
            fields=references,
            filter_=FilterNode("user_id", Operator.EQ, user_id, InstitutionAccount),
        )

        institution_account_ids: set[str] = set()
        asset_to_institution_account_id: dict[str, str] = {}
        asset_to_external_account_id: dict[str, str] = {}
        deactivated_asset_account_ids: set[str] = set()

        for row in rows:
            (
                institution_account_id,
                asset_account_id,
                asset_account_external_id,
                is_active,
            ) = row.unpack(*references)

            institution_account_ids.add(institution_account_id)
            asset_to_institution_account_id[asset_account_id] = institution_account_id
            asset_to_external_account_id[asset_account_id]  = asset_account_external_id
            if not is_active:
                deactivated_asset_account_ids.add(asset_account_id)

        return UserAccountsMap(
            user_id,
            institution_account_ids,
            asset_to_institution_account_id,
            asset_to_external_account_id,
            deactivated_asset_account_ids,
        )

    def _institution_account_to_values(
        self, account: InstitutionAccount
    ) -> dict[str, Any]:
        return {
            "id": account.id,
            "institution_id": account.institution_id,
            "user_id": account.user_id,
            "name": account.name,
            "created_on": account.created_on,
            "last_synced_at": account.last_synced_at,
        }

    def _asset_account_to_values(self, account: AssetAccount) -> dict[str, Any]:
        return {
            "id": account.id,
            "external_id": account.external_id,
            "institution_account_id": account.institution_account_id,
            "name": account.name,
            "is_active": account.is_active,
        }

    def _row_to_institution_account(self, row: dict[FieldReference, Any]) -> InstitutionAccount:
        def field_referece(field: str) -> FieldReference:
            return FieldReference(field, InstitutionAccount)

        return InstitutionAccount(
            id=row[field_referece("id")],
            user_id=row[field_referece("user_id")],
            institution_id=self._institution_registry.get_institution_id(
                row[field_referece("institution_id")]
            ),
            name=row[field_referece("name")],
            created_on=row[field_referece("created_on")],
            last_synced_at=row[field_referece("last_synced_at")],
        )

    def _row_to_asset_account(self, row: dict[FieldReference, Any]) -> AssetAccount:
        def field_referece(field: str) -> FieldReference:
            return FieldReference(field, AssetAccount)
        
        return AssetAccount(
            id=row[field_referece("id")],
            external_id=row[field_referece("external_id")],
            institution_account_id=row[field_referece("institution_account_id")],
            name=row[field_referece("name")],
            is_active=bool(row[field_referece("is_active")]),
        )
