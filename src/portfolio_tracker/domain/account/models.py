import uuid
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, datetime

from portfolio_tracker.domain.institution import InstitutionId


@dataclass(frozen=True)
class InstitutionAccount:
    user_id: str
    institution_id: InstitutionId
    name: str
    created_on: date
    last_synced_at: datetime | None
    id: str = field(default_factory=lambda: f"inst_acc_{uuid.uuid4().hex[:16]}")

    def with_last_synced_at(self, last_synced_at: datetime) -> InstitutionAccount:
        return replace(self, last_synced_at=last_synced_at)


@dataclass(frozen=True)
class AssetAccount:
    institution_account_id: str
    external_id: str
    name: str
    is_active: bool = True
    id: str = field(default_factory=lambda: f"ast_acc_{uuid.uuid4().hex[:16]}")


@dataclass
class UserAccountsMap:
    user_id: str
    institution_account_ids: set[str]
    asset_to_institution_account_id: dict[str, str]
    asset_to_external_account_id: dict[str, str]
    deactivated_asset_account_ids: set[str]
    institution_to_asset_account_ids: dict[str, set[str]] = field(
        default_factory=lambda: defaultdict(set), init=False
    )
    instituion_to_external_account_ids: dict[str, set[str]] = field(
        default_factory=lambda: defaultdict(set), init=False
    )
    external_to_asset_account_id: dict[str, str] = field(
        default_factory=dict, init=False
    )

    def __post_init__(self) -> None:
        for (
            asset_account_id,
            institution_account_id,
        ) in self.asset_to_institution_account_id.items():
            external_id = self.asset_to_external_account_id[asset_account_id]
            self.institution_to_asset_account_ids[institution_account_id].add(
                asset_account_id
            )
            self.instituion_to_external_account_ids[institution_account_id].add(
                external_id
            )
            self.external_to_asset_account_id[external_id] = asset_account_id

    @property
    def all_asset_account_ids(self) -> set[str]:
        return set(self.asset_to_institution_account_id.keys())

    @property
    def all_asset_account_external_ids(self) -> set[str]:
        return set(self.asset_to_external_account_id.values())

    @property
    def activated_asset_account_ids(self) -> set[str]:
        return self.all_asset_account_ids - self.deactivated_asset_account_ids

    def add_asset_account(self, account: AssetAccount) -> None:
        self.asset_to_institution_account_id[account.id] = account.institution_account_id
        self.asset_to_external_account_id[account.id] = account.external_id
        self.institution_to_asset_account_ids[account.institution_account_id].add(
            account.id
        )
        self.instituion_to_external_account_ids[account.institution_account_id].add(account.external_id)
        self.external_to_asset_account_id[account.external_id] = account.id

    def resolve_institution_account_ids(
        self,
        institution_account_ids: set[str] | None = None,
        asset_account_ids: set[str] | None = None,
    ) -> set[str]:
        if not institution_account_ids and not asset_account_ids:
            return self.institution_account_ids

        result: set[str] = set()

        if institution_account_ids:
            result.update(institution_account_ids)

        if asset_account_ids:
            result.update(
                self.asset_to_institution_account_id[asset_account_id]
                for asset_account_id in asset_account_ids
            )

        return result

    def resolve_asset_account_ids(
        self,
        institution_account_ids: set[str] | None = None,
        asset_account_ids: set[str] | None = None,
    ) -> set[str]:
        if not institution_account_ids and not asset_account_ids:
            return self.all_asset_account_ids

        result: set[str] = set()

        if institution_account_ids:
            for institution_account_id in institution_account_ids:
                result.update(
                    self.institution_to_asset_account_ids[institution_account_id]
                )

        if asset_account_ids:
            result.update(asset_account_ids)

        return result

    def resolve_asset_account_external_ids(
        self,
        institution_account_ids: set[str] | None = None,
        asset_account_ids: set[str] | None = None,
    ) -> set[str]:
        if not institution_account_ids and not asset_account_ids:
            return self.all_asset_account_external_ids

        all_asset_account_ids: set[str] = set()

        if institution_account_ids:
            for institution_account_id in institution_account_ids:
                all_asset_account_ids.update(
                    self.institution_to_asset_account_ids[institution_account_id]
                )

        if asset_account_ids:
            all_asset_account_ids.update(asset_account_ids)

        return {
            self.asset_to_external_account_id[asset_account_id]
            for asset_account_id in all_asset_account_ids
        }
