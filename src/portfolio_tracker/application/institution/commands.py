from dataclasses import dataclass
from datetime import date
from typing import Any

from portfolio_tracker.domain.institution import InstitutionId


@dataclass(frozen=True)
class ConnectInstitutionCommand:
    institution_id: InstitutionId
    name: str
    account_opened_on: date
    credential_parameters: dict[str, Any]


@dataclass(frozen=True)
class UpdateInstitutionConnectionCommand:
    institution_connection_id: str
    name: str
    account_opened_on: date
    credential_parameters: dict[str, Any] | None
