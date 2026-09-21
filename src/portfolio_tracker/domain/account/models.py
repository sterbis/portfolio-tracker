import secrets
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True)
class AssetAccount:
    id: str = field(default_factory=lambda: f"acc_{secrets.token_urlsafe(8)}")
    institution_connection_id: str
    external_id: str
    name: str
    is_active: bool = True


@dataclass(frozen=True, kw_only=True)
class AccountMap:
    user_id: str
    institution_connection_ids: set[str]
    account_id_to_institution_connection_id: dict[str, str]
    account_id_to_account_external_id: dict[str, str]
    deactivated_account_ids: set[str]
    institution_connection_id_to_account_ids: dict[str, set[str]] = field(
        default_factory=lambda: defaultdict(set), init=False
    )
    account_external_id_to_account_id: dict[str, str] = field(
        default_factory=dict, init=False
    )

    def __post_init__(self) -> None:
        for (
            account_id,
            institution_connection_id,
        ) in self.account_id_to_institution_connection_id.items():
            account_external_id = self.account_id_to_account_external_id[account_id]
            self.institution_connection_id_to_account_ids[
                institution_connection_id
            ].add(account_id)
            self.account_external_id_to_account_id[account_external_id] = account_id

    @property
    def account_ids(self) -> set[str]:
        return set(self.account_id_to_institution_connection_id.keys())

    @property
    def account_external_ids(self) -> set[str]:
        return set(self.account_id_to_account_external_id.values())

    @property
    def activated_account_ids(self) -> set[str]:
        return self.account_ids - self.deactivated_account_ids

    def add_account(self, account: AssetAccount) -> None:
        self.account_id_to_institution_connection_id[account.id] = (
            account.institution_connection_id
        )
        self.account_id_to_account_external_id[account.id] = account.external_id
        self.institution_connection_id_to_account_ids[
            account.institution_connection_id
        ].add(account.id)
        self.account_external_id_to_account_id[account.external_id] = account.id

    def resolve_institution_connection_ids(
        self,
        institution_connection_ids: set[str] | None = None,
        account_ids: set[str] | None = None,
    ) -> set[str]:
        if not institution_connection_ids and not account_ids:
            return self.institution_connection_ids

        result: set[str] = set()

        if institution_connection_ids:
            result.update(institution_connection_ids)

        if account_ids:
            result.update(
                self.account_id_to_institution_connection_id[account_id]
                for account_id in account_ids
            )

        return result

    def resolve_account_ids(
        self,
        institution_connection_ids: set[str] | None = None,
        account_ids: set[str] | None = None,
    ) -> set[str]:
        if not institution_connection_ids and not account_ids:
            return self.account_ids

        result: set[str] = set()

        if institution_connection_ids:
            for institution_connection_id in institution_connection_ids:
                result.update(
                    self.institution_connection_id_to_account_ids[
                        institution_connection_id
                    ]
                )

        if account_ids:
            result.update(account_ids)

        return result

    def resolve_account_external_ids(
        self,
        institution_connection_ids: set[str] | None = None,
        account_ids: set[str] | None = None,
    ) -> set[str]:
        if not institution_connection_ids and not account_ids:
            return self.account_external_ids

        all_account_ids: set[str] = set()

        if institution_connection_ids:
            for institution_connection_id in institution_connection_ids:
                all_account_ids.update(
                    self.institution_connection_id_to_account_ids[
                        institution_connection_id
                    ]
                )

        if account_ids:
            all_account_ids.update(account_ids)

        return {
            self.account_id_to_account_external_id[account_id]
            for account_id in all_account_ids
        }
