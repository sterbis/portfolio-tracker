from dataclasses import replace
from datetime import datetime, time, timezone

from portfolio_tracker.application.contracts.commands import (
    ConnectInstitutionAccountCommand,
    UpdateInstitutionAccountCommand,
)
from portfolio_tracker.application.ports.unit_of_work import UnitOfWork
from portfolio_tracker.domain.accounts import InstitutionAccount
from portfolio_tracker.domain.institution import Credentials, InstitutionRegistry


class AccountService:
    def __init__(
        self, institution_registry: InstitutionRegistry, uow: UnitOfWork
    ) -> None:
        self._institution_registry = institution_registry
        self._uow = uow

    def connect_institution_account(
        self, user_id: str, command: ConnectInstitutionAccountCommand
    ) -> str:
        self._validate_credentials_type(command.institution_id, command.credentials)

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
                raise ValueError("Institution account not found.")

            if command.credentials:
                self._validate_credentials_type(
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

    def disconnect_institution_account(self, institution_account_id: str) -> None:
        with self._uow as uow:
            uow.accounts.remove_institution_account_by_id(institution_account_id)
            uow.commit()

    def _validate_credentials_type(
        self, institution_id: str, credentials: Credentials
    ) -> None:
        institution = self._institution_registry.get(institution_id)
        if not isinstance(credentials, institution.credentials_cls):
            raise ValueError(
                f"Invalid {institution.name} credentials. "
                f"Expected {institution.credentials_cls.__name__}, got {type(credentials).__name__}."
            )
