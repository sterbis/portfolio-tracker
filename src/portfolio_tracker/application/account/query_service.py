from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import StorageConnectionFactory
from portfolio_tracker.application.shared.filter import FilterMapper, FilterSplitter
from portfolio_tracker.application.shared.service import QueryService
from portfolio_tracker.application.views import (
    AssetAccountOverviewView,
    InstitutionAccountOverviewView,
    InstitutionAccountView,
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

    def get_accounts_overview(
        self, user_id: str
    ) -> list[InstitutionAccountOverviewView]:
        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            accounts_overview: list[InstitutionAccountOverviewView] = []
            institution_accounts = uow.accounts.get_institution_accounts_by_user_id(
                user_id
            )
            for institution_account in institution_accounts:
                institution = self._institution_registry.get_institution(
                    institution_account.institution_id
                )
                asset_accounts = (
                    uow.accounts.get_asset_accounts_by_institution_account_id(
                        institution_account.id
                    )
                )
                accounts_overview.append(
                    InstitutionAccountOverviewView.from_domain(
                        institution_account=institution_account,
                        institution_view=InstitutionView.from_domain(institution),
                        asset_account_overview_views=[
                            AssetAccountOverviewView.from_domain(asset_account)
                            for asset_account in asset_accounts
                        ],
                    )
                )

            return accounts_overview

    def get_institution_account(
        self, user_id: str, account_id: str
    ) -> InstitutionAccountView:
        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            institution_account = uow.accounts.get_institution_account_by_id(account_id)
            institution = self._institution_registry.get_institution(
                institution_account.institution_id
            )
            credentials = uow.credentials.get(institution_account.id)

            return InstitutionAccountView.from_domain(
                institution_account=institution_account,
                institution_view=InstitutionView.from_domain(institution),
                credentials=credentials,
            )

    def get_asset_account_overview(
        self, user_id: str, account_id: str
    ) -> AssetAccountOverviewView:
        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            asset_account = uow.accounts.get_asset_account_by_id(account_id)
            return AssetAccountOverviewView.from_domain(asset_account)
