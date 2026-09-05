from typing import Any

from portfolio_tracker.application.persistence import StorageConnectionFactory
from portfolio_tracker.application.shared.service import Service
from portfolio_tracker.domain.institution import Credentials, Institution, InstitutionId

from .registry import InstitutionRegistry


class InstitutionService(Service):
    def __init__(
        self, storage_connection_factory: StorageConnectionFactory, institution_registry: InstitutionRegistry
    ) -> None:
        super().__init__(storage_connection_factory)
        self._institution_registry = institution_registry

    def get_institution(self, institution_id: InstitutionId) -> Institution:
        return self._institution_registry.get_institution(institution_id)

    def get_credentials_cls(
        self, institution_id: InstitutionId
    ) -> type[Credentials]:
        return self._institution_registry.get_credentials_cls(institution_id)

    def parse_credential_parameters(
        self, institution_id: InstitutionId, parameters: dict[str, str]
    ) -> dict[str, Any]:
        return self._institution_registry.parse_credential_parameters(
            institution_id, parameters
        )
