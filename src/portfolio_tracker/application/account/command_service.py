from dataclasses import replace

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import StorageConnection, UnitOfWork
from portfolio_tracker.application.shared.errors import (
    AssetAccountAlreadyActivatedError,
    AssetAccountAlreadyDeactivatedError,
    AssetAccountNotFoundError,
)
from portfolio_tracker.application.shared.service import CommandService
from portfolio_tracker.domain.account import AssetAccount

from .commands import UpdateAssetAccountCommand


class AccountCommandService(CommandService):
    def __init__(
        self,
        storage_connection: StorageConnection,
        institution_registry: InstitutionRegistry,
    ) -> None:
        super().__init__(storage_connection)
        self._institution_registry = institution_registry

    def update_account(self, user_id: str, command: UpdateAssetAccountCommand) -> None:
        with self._unit_of_work(user_id) as uow:
            account = self._get_account(uow, command.account_id)
            account = replace(
                account,
                external_id=command.external_id,
                name=command.name,
            )
            uow.accounts.update(account)
            uow.commit()

    def activate_account(self, user_id: str, account_id: str) -> None:
        with self._unit_of_work(user_id) as uow:
            account = self._get_account(uow, account_id)
            if account.is_active:
                raise AssetAccountAlreadyActivatedError(account_id)

            account = replace(account, is_active=True)
            uow.accounts.update(account)
            uow.commit()

    def deactivate_account(self, user_id: str, account_id: str) -> None:
        with self._unit_of_work(user_id) as uow:
            account = self._get_account(uow, account_id)
            if not account.is_active:
                raise AssetAccountAlreadyDeactivatedError(account_id)

            account = replace(account, is_active=False)
            uow.accounts.update(account)
            uow.transactions.remove_by_account_id(account.id)
            uow.commit()

    def _get_account(self, uow: UnitOfWork, account_id: str) -> AssetAccount:
        account = uow.accounts.get_by_id(account_id)
        if account is None:
            raise AssetAccountNotFoundError(account_id)

        return account
