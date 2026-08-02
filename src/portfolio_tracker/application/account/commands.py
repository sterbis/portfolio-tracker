from dataclasses import dataclass
from datetime import date

from portfolio_tracker.domain.institution import Credentials, InstitutionId


@dataclass(frozen=True)
class ConnectInstitutionAccountCommand:
    institution_id: InstitutionId
    name: str
    created_on: date
    credentials: Credentials


@dataclass(frozen=True)
class UpdateInstitutionAccountCommand:
    institution_account_id: str
    name: str
    created_on: date
    credentials: Credentials | None


@dataclass(frozen=True)
class UpdateAssetAccountCommand:
    asset_account_id: str
    external_id: str
    name: str
