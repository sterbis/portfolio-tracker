from dataclasses import dataclass

from portfolio_tracker.domain.institution import Institution, InstitutionId


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
