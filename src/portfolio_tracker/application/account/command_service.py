from dataclasses import replace

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import StorageConnectionFactory
from portfolio_tracker.application.shared.errors import (
    AssetAccountAlreadyActivatedError,
    AssetAccountAlreadyDeactivatedError,
)
from portfolio_tracker.application.shared.service import Service

from .commands import UpdateAssetAccountCommand


class AccountCommandService(Service):
    def __init__(
        self,
        storage_connection_factory: StorageConnectionFactory,
        institution_registry: InstitutionRegistry,
    ) -> None:
        super().__init__(storage_connection_factory)
        self._institution_registry = institution_registry

    def update_account(self, user_id: str, command: UpdateAssetAccountCommand) -> None:
        with self._user_scoped_unit_of_work(user_id) as uow:
            account = uow.accounts.get_by_id(command.account_id)
            account = replace(
                account,
                external_id=command.external_id,
                name=command.name,
            )
            uow.accounts.update(account)
            uow.commit()

    def activate_account(self, user_id: str, account_id: str) -> None:
        with self._user_scoped_unit_of_work(user_id) as uow:
            account = uow.accounts.get_by_id(account_id)
            if account.is_active:
                raise AssetAccountAlreadyActivatedError(account_id)

            account = replace(account, is_active=True)
            uow.accounts.update(account)
            uow.commit()

    def deactivate_account(self, user_id: str, account_id: str) -> None:
        with self._user_scoped_unit_of_work(user_id) as uow:
            account = uow.accounts.get_by_id(account_id)
            if not account.is_active:
                raise AssetAccountAlreadyDeactivatedError(account_id)

            account = replace(account, is_active=False)
            uow.accounts.update(account)
            uow.transactions.remove_by_asset_account_id(account.id)
            uow.commit()
