import uuid
from dataclasses import dataclass, field, replace
from datetime import date, datetime

from portfolio_tracker.domain.institution import InstitutionId


@dataclass(frozen=True)
class InstitutionAccount:
    user_id: str
    institution_id: InstitutionId
    name: str
    created_on: date
    last_synced_at: datetime
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
