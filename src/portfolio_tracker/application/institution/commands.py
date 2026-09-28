from dataclasses import dataclass
from datetime import date
from typing import Any

from portfolio_tracker.domain.institution import InstitutionId


@dataclass(frozen=True)
class ConnectInstitutionCommand:
    institution_id: InstitutionId
    name: str
    sync_from: date
    credential_parameters: dict[str, Any]


@dataclass(frozen=True)
class UpdateInstitutionConnectionCommand:
    connection_id: str
    name: str
    sync_from: date
    credential_parameters: dict[str, Any] | None
