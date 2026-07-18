from portfolio_tracker.domain.institution import Institution

from .exceptions import InstitutionNotFoundError


class InstitutionRegistry:
    def __init__(self, institutions: dict[str, Institution]) -> None:
        self._institutions = institutions

    def get(self, institution_id: str) -> Institution:
        if institution_id not in self._institutions:
            raise InstitutionNotFoundError(institution_id)

        return self._institutions[institution_id]
