from portfolio_tracker.domain.institution import Institution, InstitutionId

from .exceptions import InstitutionNotFoundError


class InstitutionRegistry:
    def __init__(
        self,
        institutions: dict[InstitutionId, Institution],
        institution_id_cls: type[InstitutionId],
    ) -> None:
        self._institutions = institutions
        self._institution_id_cls = institution_id_cls

    @property
    def institution_id_cls(self) -> type[InstitutionId]:
        return self._institution_id_cls

    def get(self, institution_id: InstitutionId) -> Institution:
        if institution_id not in self._institutions:
            raise InstitutionNotFoundError(institution_id)

        return self._institutions[institution_id]
