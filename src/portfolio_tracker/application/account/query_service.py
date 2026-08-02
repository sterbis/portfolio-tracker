from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import SessionFactory
from portfolio_tracker.application.shared.service import ApplicationService
from portfolio_tracker.application.shared.dtos import (
    AssetAccountOverviewDto,
    InstitutionAccountDto,
    InstitutionAccountOverviewDto,
    InstitutionDto,
)


class AccountQueryService(ApplicationService):
    def __init__(
        self,
        session_factory: SessionFactory,
        institution_registry: InstitutionRegistry
    ) -> None:
        super().__init__(session_factory)
        self._institution_registry = institution_registry

    def get_accounts_overview(
        self, user_id: str
    ) -> list[InstitutionAccountOverviewDto]:
        with self._user_unit_of_work(user_id, read_only=True) as uow:
            accounts_overview: list[InstitutionAccountOverviewDto] = []
            institution_accounts = uow.accounts.get_institution_accounts_by_user_id(
                user_id
            )
            for institution_account in institution_accounts:
                institution = self._institution_registry.get(
                    institution_account.institution_id
                )
                asset_accounts = (
                    uow.accounts.get_asset_accounts_by_institution_account_id(
                        institution_account.id
                    )
                )
                accounts_overview.append(
                    InstitutionAccountOverviewDto.from_domain(
                        institution_account=institution_account,
                        institution_dto=InstitutionDto.from_domain(institution),
                        asset_account_overviews=[
                            AssetAccountOverviewDto.from_domain(asset_account)
                            for asset_account in asset_accounts
                        ],
                    )
                )

            return accounts_overview

    def get_institution_account(self, user_id: str, account_id: str) -> InstitutionAccountDto:
        with self._user_unit_of_work(user_id, read_only=True) as uow:
            institution_account = uow.accounts.get_institution_account_by_id(account_id)
            institution = self._institution_registry.get(
                institution_account.institution_id
            )
            credentials = uow.credentials.retrieve(institution_account.id)

            return InstitutionAccountDto.from_domain(
                institution_account=institution_account,
                institution_dto=InstitutionDto.from_domain(institution),
                credentials=credentials,
            )

    def get_asset_account_overview(self, user_id: str, account_id: str) -> AssetAccountOverviewDto:
        with self._user_unit_of_work(user_id, read_only=True) as uow:
            asset_account = uow.accounts.get_asset_account_by_id(account_id)
            return AssetAccountOverviewDto.from_domain(asset_account)
