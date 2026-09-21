from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import StorageConnectionFactory
from portfolio_tracker.application.shared.filter import FilterMapper, FilterSplitter
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

    def get_account(self, user_id: str, account_id: str) -> AssetAccountView:
        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            account = uow.accounts.get_by_id(account_id)
            institution_connection = uow.institution_connections.get_by_id(
                account.institution_connection_id
            )
            institution = self._institution_registry.get_institution(
                institution_connection.institution_id
            )
            return AssetAccountView.from_domain(
                account,
                institution_connection_view=InstitutionConnectionView.from_domain(
                    institution_connection,
                    institution_view=InstitutionView.from_domain(institution),
                ),
            )

    def get_accounts(self, user_id: str) -> list[AssetAccountView]:
        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            accounts = uow.accounts.get_by_ids(uow.account_map.account_ids)
            institution_connections = uow.institution_connections.get_by_ids(
                uow.account_map.institution_connection_ids
            )
            institutions = [
                self._institution_registry.get_institution(
                    institution_connection.institution_id
                )
                for institution_connection in institution_connections
            ]
            return list(
                self._view_builder.build_account_views(
                    institutions,
                    institution_connections,
                    accounts,
                ).values()
            )
