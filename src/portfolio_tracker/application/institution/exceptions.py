from portfolio_tracker.application.contracts.exceptions import EntityNotFoundError
from portfolio_tracker.domain.institution import InstitutionId


class InstitutionClientError(Exception): ...


class InstitutionReportParserError(Exception): ...


class InstitutionNotFoundError(EntityNotFoundError):
    def __init__(self, institution_id: InstitutionId) -> None:
        super().__init__(entity_name="Institution", entity_id=institution_id.value)
