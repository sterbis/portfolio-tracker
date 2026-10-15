from collections import defaultdict
from dataclasses import dataclass, field

from portfolio_tracker.domain.shared import DeterministicIdEntity


@dataclass(frozen=True, kw_only=True)
class AssetAccount(DeterministicIdEntity):
    institution_connection_id: str
    external_id: str
    name: str
    is_active: bool = True

    @property
    def _id_prefix(self) -> str:
        return "acc"

    @property
    def _identity(self) -> str:
        return f"{self.institution_connection_id}|{self.external_id}"


@dataclass(frozen=True, kw_only=True)
class AccountMap:
    user_id: str
    connection_ids: set[str]
    account_id_to_connection_id: dict[str, str]
    account_id_to_external_id: dict[str, str]
    deactivated_account_ids: set[str]
    connection_id_to_account_ids: dict[str, set[str]] = field(
        default_factory=lambda: defaultdict(set), init=False
    )
    account_external_id_to_id: dict[str, str] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        for account_id, connection_id in self.account_id_to_connection_id.items():
            account_external_id = self.account_id_to_external_id[account_id]
            self.connection_id_to_account_ids[connection_id].add(account_id)
            self.account_external_id_to_id[account_external_id] = account_id

    @property
    def account_ids(self) -> set[str]:
        return set(self.account_id_to_connection_id.keys())

    @property
    def account_external_ids(self) -> set[str]:
        return set(self.account_id_to_external_id.values())

    @property
    def activated_account_ids(self) -> set[str]:
        return self.account_ids - self.deactivated_account_ids

    def add_account(self, account: AssetAccount) -> None:
        self.account_id_to_connection_id[account.id] = account.institution_connection_id
        self.account_id_to_external_id[account.id] = account.external_id
        self.connection_id_to_account_ids[account.institution_connection_id].add(
            account.id
        )
        self.account_external_id_to_id[account.external_id] = account.id

    def resolve_institution_connection_ids(
        self,
        connection_ids: set[str] | None = None,
        account_ids: set[str] | None = None,
    ) -> set[str]:
        if not connection_ids and not account_ids:
            return self.connection_ids

        result: set[str] = set()

        if connection_ids:
            result.update(connection_ids)

        if account_ids:
            result.update(
                self.account_id_to_connection_id[account_id]
                for account_id in account_ids
            )

        return result

    def resolve_account_ids(
        self,
        connection_ids: set[str] | None = None,
        account_ids: set[str] | None = None,
    ) -> set[str]:
        if not connection_ids and not account_ids:
            return self.account_ids

        result: set[str] = set()

        if connection_ids:
            for connection_id in connection_ids:
                result.update(self.connection_id_to_account_ids[connection_id])

        if account_ids:
            result.update(account_ids)

        return result

    def resolve_account_external_ids(
        self,
        connection_ids: set[str] | None = None,
        account_ids: set[str] | None = None,
    ) -> set[str]:
        if not connection_ids and not account_ids:
            return self.account_external_ids

        all_account_ids: set[str] = set()

        if connection_ids:
            for connection_id in connection_ids:
                all_account_ids.update(self.connection_id_to_account_ids[connection_id])

        if account_ids:
            all_account_ids.update(account_ids)

        return {
            self.account_id_to_external_id[account_id] for account_id in all_account_ids
        }
