from dataclasses import dataclass
from datetime import date, datetime

from portfolio_tracker.domain.institution import (
    Credentials,
    Institution,
    InstitutionConnection,
    InstitutionId,
)


@dataclass(frozen=True, kw_only=True)
class InstitutionView:
    id: InstitutionId
    name: str
    log_in_url: str

    @classmethod
    def from_domain(cls, institution: Institution) -> InstitutionView:
        return cls(
            id=institution.id,
            name=institution.name,
            log_in_url=institution.log_in_url,
        )


@dataclass(frozen=True, kw_only=True)
class InstitutionConnectionView:
    id: str
    institution: InstitutionView
    name: str
    account_opened_on: date
    last_synced_at: datetime | None
    credentials: Credentials | None

    @classmethod
    def from_domain(
        cls,
        institution_connection: InstitutionConnection,
        institution_view: InstitutionView,
        credentials: Credentials | None = None,
    ) -> InstitutionConnectionView:
        return cls(
            id=institution_connection.id,
            institution=institution_view,
            name=institution_connection.name,
            account_opened_on=institution_connection.account_opened_on,
            last_synced_at=institution_connection.last_synced_at,
            credentials=credentials,
        )
