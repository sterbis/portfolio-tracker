from dataclasses import dataclass
from datetime import date, datetime

from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.institution import Credentials

from .institution import InstitutionView


@dataclass(frozen=True, kw_only=True)
class InstitutionAccountView:
    id: str
    institution: InstitutionView
    name: str
    created_on: date
    last_synced_at: datetime | None
    credentials: Credentials | None

    @classmethod
    def from_domain(
        cls,
        institution_account: InstitutionAccount,
        institution_view: InstitutionView,
        credentials: Credentials | None = None,
    ) -> InstitutionAccountView:
        return cls(
            id=institution_account.id,
            institution=institution_view,
            name=institution_account.name,
            created_on=institution_account.created_on,
            last_synced_at=institution_account.last_synced_at,
            credentials=credentials,
        )


@dataclass(frozen=True, kw_only=True)
class AssetAccountView:
    id: str
    institution_account: InstitutionAccountView
    external_id: str
    name: str
    is_active: bool

    @classmethod
    def from_domain(
        cls,
        asset_account: AssetAccount,
        institution_account_view: InstitutionAccountView,
    ) -> AssetAccountView:
        return cls(
            id=asset_account.id,
            institution_account=institution_account_view,
            external_id=asset_account.external_id,
            name=asset_account.name,
            is_active=asset_account.is_active,
        )


@dataclass(frozen=True, kw_only=True)
class InstitutionAccountOverviewView:
    id: str
    institution: InstitutionView
    name: str
    created_on: date
    last_synced_at: datetime | None
    credentials: Credentials | None
    asset_accounts: list[AssetAccountOverviewView]

    @classmethod
    def from_domain(
        cls,
        institution_account: InstitutionAccount,
        institution_view: InstitutionView,
        asset_account_overview_views: list[AssetAccountOverviewView],
        credentials: Credentials | None = None,
    ) -> InstitutionAccountOverviewView:
        return cls(
            id=institution_account.id,
            institution=institution_view,
            name=institution_account.name,
            created_on=institution_account.created_on,
            last_synced_at=institution_account.last_synced_at,
            asset_accounts=asset_account_overview_views,
            credentials=credentials,
        )


@dataclass(frozen=True, kw_only=True)
class AssetAccountOverviewView:
    id: str
    institution_account_id: str
    external_id: str
    name: str
    is_active: bool

    @classmethod
    def from_domain(
        cls,
        asset_account: AssetAccount,
    ) -> AssetAccountOverviewView:
        return cls(
            id=asset_account.id,
            institution_account_id=asset_account.institution_account_id,
            external_id=asset_account.external_id,
            name=asset_account.name,
            is_active=asset_account.is_active,
        )
