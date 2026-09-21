from typing import Any

from portfolio_tracker.application.persistence import StorageConnectionFactory
from portfolio_tracker.application.shared.filter import FilterMapper, FilterSplitter
from portfolio_tracker.application.shared.service import QueryService
from portfolio_tracker.application.views import (
    InstitutionConnectionView,
    InstitutionView,
    ViewBuilder,
)
from portfolio_tracker.domain.institution import Credentials, Institution, InstitutionId

from .registry import InstitutionRegistry


class InstitutionQueryService(QueryService):
    def __init__(
        self,
        storage_connection_factory: StorageConnectionFactory,
        filter_mapper: FilterMapper,
        filter_splitter: FilterSplitter,
        view_builder: ViewBuilder,
        institution_registry: InstitutionRegistry,
    ) -> None:
        super().__init__(
            storage_connection_factory, filter_mapper, filter_splitter, view_builder
        )
        self._institution_registry = institution_registry

    def get_institution_connection(
        self, user_id: str, connection_id: str
    ) -> InstitutionConnectionView:
        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            institution_connection = uow.institution_connections.get_by_id(
                connection_id
            )
            institution = self._institution_registry.get_institution(
                institution_connection.institution_id
            )
            credentials = uow.credentials.get(institution_connection.id)

            return InstitutionConnectionView.from_domain(
                institution_connection=institution_connection,
                institution_view=InstitutionView.from_domain(institution),
                credentials=credentials,
            )

    def get_institution_connections(
        self,
        user_id: str,
    ) -> list[InstitutionConnectionView]:
        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            institution_connections = uow.institution_connections.get_by_user_id(
                user_id
            )
            institution_ids = {
                institution_connection.institution_id
                for institution_connection in institution_connections
            }
            institutions = [
                self._institution_registry.get_institution(institution_id)
                for institution_id in institution_ids
            ]
            return list(
                self._view_builder.build_institution_connection_views(
                    institutions,
                    institution_connections,
                ).values()
            )

    def get_institution(self, institution_id: InstitutionId) -> Institution:
        return self._institution_registry.get_institution(institution_id)

    def get_credentials_cls(self, institution_id: InstitutionId) -> type[Credentials]:
        return self._institution_registry.get_credentials_cls(institution_id)

    def parse_credential_parameters(
        self, institution_id: InstitutionId, parameters: dict[str, str]
    ) -> dict[str, Any]:
        return self._institution_registry.parse_credential_parameters(
            institution_id, parameters
        )
