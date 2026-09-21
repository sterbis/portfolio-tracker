from dataclasses import replace

from portfolio_tracker.application.persistence import StorageConnectionFactory
from portfolio_tracker.application.shared.errors import (
    InstitutionClientError,
    InvalidCredentialsError,
)
from portfolio_tracker.application.shared.service import Service
from portfolio_tracker.domain.institution import Credentials, InstitutionConnection

from .commands import ConnectInstitutionCommand, UpdateInstitutionConnectionCommand
from .registry import InstitutionRegistry


class InstitutionCommandService(Service):
    def __init__(
        self,
        storage_connection_factory: StorageConnectionFactory,
        institution_registry: InstitutionRegistry,
    ) -> None:
        super().__init__(storage_connection_factory)
        self._institution_registry = institution_registry

    def connect_institution(
        self, user_id: str, command: ConnectInstitutionCommand
    ) -> str:
        connection = InstitutionConnection(
            user_id=user_id,
            institution_id=command.institution_id,
            name=command.name,
            account_opened_on=command.account_opened_on,
        )
        credentials = self._institution_registry.create_credentials(
            connection.institution_id,
            connection.id,
            command.credential_parameters,
        )
        self._verify_credentials(credentials)

        with self._user_scoped_unit_of_work(user_id) as uow:
            uow.institution_connections.add(connection)
            uow.credentials.upsert(credentials)
            uow.commit()

        return connection.id

    def update_institution_connection(
        self, user_id: str, command: UpdateInstitutionConnectionCommand
    ) -> None:
        with self._user_scoped_unit_of_work(user_id) as uow:
            connection = uow.institution_connections.get_by_id(
                command.institution_connection_id
            )
            if command.credential_parameters:
                credentials = self._institution_registry.create_credentials(
                    connection.institution_id,
                    connection.id,
                    command.credential_parameters,
                )
                self._verify_credentials(credentials)
                uow.credentials.upsert(credentials)

            connection = replace(
                connection,
                name=command.name,
                account_opened_on=command.account_opened_on,
            )
            uow.institution_connections.update(connection)
            uow.commit()

    def disconnect_institution(self, user_id: str, connection_id: str) -> None:
        with self._user_scoped_unit_of_work(user_id) as uow:
            uow.institution_connections.remove_by_id(connection_id)
            uow.credentials.remove(connection_id)
            uow.commit()

    def _verify_credentials(self, credentials: Credentials) -> None:
        client = self._institution_registry.create_client(credentials)
        try:
            client.verify_connection()
        except InstitutionClientError as error:
            raise InvalidCredentialsError(credentials) from error
