from portfolio_tracker.application.contracts.dtos import (
    AssetAccountOverviewDto,
    InstitutionAccountDto,
    InstitutionAccountOverviewDto,
    InstitutionDto,
)
from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import SessionFactory

from .exceptions import AssetAccountNotFoundError, InstitutionAccountNotFoundError


class AccountQueryService:
    def __init__(
        self, institution_registry: InstitutionRegistry, session_factory: SessionFactory
    ) -> None:
        self._institution_registry = institution_registry
        self._session_factory = session_factory

    def get_accounts_overview(
        self, user_id: str
    ) -> list[InstitutionAccountOverviewDto]:
        accounts_overview: list[InstitutionAccountOverviewDto] = []

        with (
            self._session_factory.create(read_only=True) as session,
            session.unit_of_work() as uow,
        ):
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

    def get_institution_account(self, account_id: str) -> InstitutionAccountDto:
        with (
            self._session_factory.create(read_only=True) as session,
            session.unit_of_work() as uow,
        ):
            institution_account = uow.accounts.get_institution_account_by_id(account_id)
            if not institution_account:
                raise InstitutionAccountNotFoundError(account_id)

            institution = self._institution_registry.get(
                institution_account.institution_id
            )
            credentials = uow.credentials.retrieve(institution_account.id)

            return InstitutionAccountDto.from_domain(
                institution_account=institution_account,
                institution_dto=InstitutionDto.from_domain(institution),
                credentials=credentials,
            )

    def get_asset_account_overview(self, account_id: str) -> AssetAccountOverviewDto:
        with (
            self._session_factory.create(read_only=True) as session,
            session.unit_of_work() as uow,
        ):
            asset_account = uow.accounts.get_asset_account_by_id(account_id)
            if not asset_account:
                raise AssetAccountNotFoundError(account_id)

            return AssetAccountOverviewDto.from_domain(asset_account)
