from dataclasses import replace

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import SessionFactory
from portfolio_tracker.application.shared.exceptions import (
    AssetAccountAlreadyActivatedError,
    AssetAccountAlreadyDeactivatedError,
    InstitutionClientError,
    InvalidCredentialsError,
)
from portfolio_tracker.application.shared.service import ApplicationService
from portfolio_tracker.domain.account import InstitutionAccount
from portfolio_tracker.domain.institution import Credentials

from .commands import (
    ConnectInstitutionAccountCommand,
    UpdateAssetAccountCommand,
    UpdateInstitutionAccountCommand,
)


class AccountCommandService(ApplicationService):
    def __init__(
        self,
        session_factory: SessionFactory,
        institution_registry: InstitutionRegistry,
    ) -> None:
        super().__init__(session_factory)
        self._institution_registry = institution_registry

    def connect_institution_account(
        self, user_id: str, command: ConnectInstitutionAccountCommand
    ) -> str:
        institution_account = InstitutionAccount(
            user_id=user_id,
            institution_id=command.institution_id,
            name=command.name,
            created_on=command.created_on,
        )
        credentials = self._institution_registry.create_credentials(
            institution_account.institution_id,
            institution_account.id,
            command.credentials_data,
        )
        self._verify_credentials(credentials)

        with self._user_unit_of_work(user_id) as uow:
            uow.accounts.add_institution_account(institution_account)
            uow.credentials.store(credentials)
            uow.commit()

        return institution_account.id

    def update_institution_account(
        self, user_id: str, command: UpdateInstitutionAccountCommand
    ) -> None:
        with self._user_unit_of_work(user_id) as uow:
            institution_account = uow.accounts.get_institution_account_by_id(
                command.institution_account_id
            )
            if command.credentials_data:
                credentials = self._institution_registry.create_credentials(
                    institution_account.institution_id,
                    institution_account.id,
                    command.credentials_data,
                )
                self._verify_credentials(credentials)
                uow.credentials.store(credentials)

            institution_account = replace(
                institution_account,
                name=command.name,
                created_on=command.created_on,
            )
            uow.accounts.update_institution_account(institution_account)
            uow.commit()

    def disconnect_institution_account(self, user_id: str, account_id: str) -> None:
        with self._user_unit_of_work(user_id) as uow:
            uow.accounts.remove_institution_account_by_id(account_id)
            uow.credentials.remove(account_id)
            uow.commit()

    def update_asset_account(
        self, user_id: str, command: UpdateAssetAccountCommand
    ) -> None:
        with self._user_unit_of_work(user_id) as uow:
            asset_account = uow.accounts.get_asset_account_by_id(
                command.asset_account_id
            )
            asset_account = replace(
                asset_account,
                external_id=command.external_id,
                name=command.name,
            )
            uow.accounts.update_asset_account(asset_account)
            uow.commit()

    def activate_asset_account(self, user_id: str, account_id: str) -> None:
        with self._user_unit_of_work(user_id) as uow:
            asset_account = uow.accounts.get_asset_account_by_id(account_id)
            if asset_account.is_active:
                raise AssetAccountAlreadyActivatedError(account_id)

            asset_account = replace(asset_account, is_active=True)
            uow.accounts.update_asset_account(asset_account)
            uow.commit()

    def deactivate_asset_account(self, user_id: str, account_id: str) -> None:
        with self._user_unit_of_work(user_id) as uow:
            asset_account = uow.accounts.get_asset_account_by_id(account_id)
            if not asset_account.is_active:
                raise AssetAccountAlreadyDeactivatedError(account_id)

            asset_account = replace(asset_account, is_active=False)
            uow.accounts.update_asset_account(asset_account)
            uow.transactions.remove_by_asset_account_id(asset_account.id)
            uow.commit()

    def _verify_credentials(self, credentials: Credentials) -> None:
        client = self._institution_registry.create_client(credentials)
        try:
            client.verify_connection()
        except InstitutionClientError as error:
            raise InvalidCredentialsError(credentials) from error
