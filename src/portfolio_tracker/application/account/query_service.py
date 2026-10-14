from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import StorageReadConnectionFactory
from portfolio_tracker.application.shared.filter_mapper import FilterMapper
from portfolio_tracker.application.shared.service import QueryService
from portfolio_tracker.application.views import (
    AssetAccountView,
    InstitutionConnectionView,
    InstitutionView,
    ViewBuilder,
)


class AccountQueryService(QueryService):
    def __init__(
        self,
        storage_connection_factory: StorageReadConnectionFactory,
        filter_mapper: FilterMapper,
        view_builder: ViewBuilder,
        institution_registry: InstitutionRegistry,
    ) -> None:
        super().__init__(
            storage_connection_factory, filter_mapper, view_builder
        )
        self._institution_registry = institution_registry

    def get_account(self, user_id: str, account_id: str) -> AssetAccountView:
        with self._unit_of_work(user_id) as uow:
            account = uow.accounts.get_by_id_required(account_id)
            connection = uow.institution_connections.get_by_id_required(
                account.institution_connection_id
            )
            institution = self._institution_registry.get_institution(
                connection.institution_id
            )
            return AssetAccountView.from_domain(
                account,
                connection_view=InstitutionConnectionView.from_domain(
                    connection,
                    institution_view=InstitutionView.from_domain(institution),
                ),
            )

    def get_accounts(self, user_id: str) -> list[AssetAccountView]:
        with self._unit_of_work(user_id) as uow:
            accounts = uow.accounts.get_by_user_id(user_id)
            connections = uow.institution_connections.get_by_user_id(user_id)
            institutions = [
                self._institution_registry.get_institution(connection.institution_id)
                for connection in connections
            ]
            return list(
                self._view_builder.build_account_views(
                    institutions,
                    connections,
                    accounts,
                ).values()
            )
