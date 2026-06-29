from dataclasses import replace
from datetime import datetime, time, timezone

from portfolio_tracker.application.contracts.commands import (
    ConnectInstitutionAccountCommand,
    UpdateInstitutionAccountCommand,
)
from portfolio_tracker.application.ports.encryptor import Encryptor
from portfolio_tracker.application.ports.unit_of_work import UnitOfWork
from portfolio_tracker.domain.accounts import InstitutionAccount

from .institutions import SUPPORTED_INSTITUTIONS, Credentials


class AccountService:
    def __init__(self, uow: UnitOfWork, encryption_service: Encryptor):
        self._uow = uow
        self._encryption_service = encryption_service

    def connect_institution_account(
        self, user_id: str, command: ConnectInstitutionAccountCommand
    ) -> str:
        self._validate_credentials_type(command.institution_id, command.credentials)
        encrypted_credentials = self._encryption_service.encrypt(
            command.credentials.to_json()
        )

        with self._uow as uow:
            institution_account = InstitutionAccount(
                user_id=user_id,
                institution_id=command.institution_id,
                name=command.name,
                created_on=command.created_on,
                encrypted_credentials=encrypted_credentials,
                last_synced_at=datetime.combine(
                    command.created_on,
                    time.min,
                    tzinfo=timezone.utc,
                ),
            )
            uow.accounts.add_institution_account(institution_account)
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
                encrypted_credentials = self._encryption_service.encrypt(
                    command.credentials.to_json()
                )
            else:
                encrypted_credentials = institution_account.encrypted_credentials

            institution_account = replace(
                institution_account,
                name=command.name,
                created_on=command.created_on,
                encrypted_credentials=encrypted_credentials,
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
        institution = SUPPORTED_INSTITUTIONS.get(institution_id)
        if not institution:
            raise ValueError(f"Unsupported institution {institution_id}.")

        if not isinstance(credentials, institution.credentials):
            raise ValueError(
                f"Invalid {institution.name} credentials. "
                f"Expected {institution.credentials.__name__}, got {type(credentials).__name__}."
            )
