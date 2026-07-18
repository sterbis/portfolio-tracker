from dataclasses import replace
from datetime import datetime, time, timezone
from typing import Callable

from filterutils import FilterNode, Operator

from portfolio_tracker.application.contracts.commands import (
    ConnectInstitutionAccountCommand,
    UpdateAssetAccountCommand,
    UpdateInstitutionAccountCommand,
)
from portfolio_tracker.application.institution import InstitutionClient, InstitutionClientError, InstitutionRegistry
from portfolio_tracker.application.persistence import UnitOfWork
from portfolio_tracker.domain.account import InstitutionAccount
from portfolio_tracker.domain.institution import Credentials

from .exceptions import (
    AssetAccountAlreadyActivatedError,
    AssetAccountAlreadyDeactivatedError,
    AssetAccountNotFoundError,
    InstitutionAccountNotFoundError,
    InvalidCredentialsError,
)


class AccountCommandService:
    def __init__(
        self,
        institution_registry: InstitutionRegistry,
        uow: UnitOfWork,
        client_factory: Callable[[str, Credentials], InstitutionClient[Credentials]],
    ) -> None:
        self._institution_registry = institution_registry
        self._uow = uow
        self._client_factory = client_factory

    def connect_institution_account(
        self, user_id: str, command: ConnectInstitutionAccountCommand
    ) -> str:
        self._validate_credentials(command.institution_id, command.credentials)

        with self._uow as uow:
            institution_account = InstitutionAccount(
                user_id=user_id,
                institution_id=command.institution_id,
                name=command.name,
                created_on=command.created_on,
                last_synced_at=datetime.combine(
                    command.created_on,
                    time.min,
                    tzinfo=timezone.utc,
                ),
            )
            uow.accounts.add_institution_account(institution_account)
            uow.credentials.store(institution_account.id, command.credentials)

            uow.commit()

        return institution_account.id

    def update_institution_account(
        self, command: UpdateInstitutionAccountCommand
    ) -> None:
        with self._uow as uow:
            institution_account = uow.accounts.get_institution_account_by_id(
                command.institution_account_id
            )
            if not institution_account:
                raise InstitutionAccountNotFoundError(command.institution_account_id)

            if command.credentials:
                self._validate_credentials(
                    institution_account.institution_id, command.credentials
                )
                uow.credentials.store(institution_account.id, command.credentials)

            institution_account = replace(
                institution_account,
                name=command.name,
                created_on=command.created_on,
            )
            uow.accounts.update_institution_account(institution_account)
            uow.commit()

    def disconnect_institution_account(self, account_id: str) -> None:
        with self._uow as uow:
            uow.accounts.remove_institution_account_by_id(account_id)
            uow.credentials.remove(account_id)
            uow.commit()

    def update_asset_account(
        self, command: UpdateAssetAccountCommand
    ) -> None:
        with self._uow as uow:
            asset_account = uow.accounts.get_asset_account_by_id(
                command.asset_account_id
            )
            if not asset_account:
                raise AssetAccountNotFoundError(command.asset_account_id)

            asset_account = replace(
                asset_account,
                external_id=command.external_id,
                name=command.name,
            )
            uow.accounts.update_asset_account(asset_account)
            uow.commit()

    def delete_asset_account(self, account_id: str) -> None:
        with self._uow as uow:
            uow.accounts.remove_asset_account_by_id(account_id)
            uow.commit()

    def activate_asset_account(
        self, account_id: str
    ) -> None:
        with self._uow as uow:
            asset_account = uow.accounts.get_asset_account_by_id(account_id)
            if not asset_account:
                raise AssetAccountNotFoundError(account_id)
            
            if asset_account.is_active:
                raise AssetAccountAlreadyActivatedError(account_id)

            asset_account = replace(asset_account, is_active=True)

            uow.accounts.update_asset_account(asset_account)
            uow.commit()

    def deactivate_asset_account(
        self, account_id: str
    ) -> None:
        with self._uow as uow:
            asset_account = uow.accounts.get_asset_account_by_id(account_id)
            if not asset_account:
                raise AssetAccountNotFoundError(account_id)
            
            if not asset_account.is_active:
                raise AssetAccountAlreadyDeactivatedError(account_id)

            asset_account = replace(asset_account, is_active=False)

            uow.accounts.update_asset_account(asset_account)
            uow.transactions.remove(
                filter_=FilterNode("asset_account_id", Operator.EQ, account_id)
            )
            uow.commit()

    def _validate_credentials(
        self, institution_id: str, credentials: Credentials
    ) -> None:
        client = self._client_factory(institution_id, credentials)
        try:
            client.verify_connection()

        except InstitutionClientError as error:
            raise InvalidCredentialsError(institution_id, credentials) from error
