from dataclasses import dataclass
from datetime import date
from typing import Any

from portfolio_tracker.domain.institution import InstitutionId


@dataclass(frozen=True)
class ConnectInstitutionAccountCommand:
    institution_id: InstitutionId
    name: str
    created_on: date
    credentials_data: dict[str, Any]


@dataclass(frozen=True)
class UpdateInstitutionAccountCommand:
    institution_account_id: str
    name: str
    created_on: date
    credentials_data: dict[str, Any] | None


@dataclass(frozen=True)
class UpdateAssetAccountCommand:
    asset_account_id: str
    external_id: str
    name: str
