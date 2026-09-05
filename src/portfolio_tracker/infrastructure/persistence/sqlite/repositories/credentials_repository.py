import json
from typing import Any

from portfolio_tracker.application.encryption import Encryptor
from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import CredentialsRepository
from portfolio_tracker.domain.institution import Credentials
from portfolio_tracker.infrastructure.persistence.sqlite.executor import SqliteExecutor


class SqliteCredentialsRepository(CredentialsRepository):
    def __init__(
        self,
        institution_registry: InstitutionRegistry,
        encryptor: Encryptor,
        executor: SqliteExecutor,
    ) -> None:
        super().__init__(institution_registry)
        self._encryptor = encryptor
        self._executor = executor

    def upsert(self, credentials: Credentials) -> None:
        json_string = json.dumps(credentials.parameters)
        encrypted_parameters = self._encryptor.encrypt(json_string)

        self._executor.execute(
            sql="""
                INSERT INTO credentials (institution_id, institution_account_id, encrypted_parameters)
                VALUES (:institution_id, :institution_account_id, :encrypted_parameters)
                ON CONFLICT(institution_account_id) DO UPDATE SET
                encrypted_parameters = EXCLUDED.encrypted_parameters;
            """,
            parameters={
                "institution_id": credentials.institution_id,
                "institution_account_id": credentials.institution_account_id,
                "encrypted_parameters": encrypted_parameters,
            },
        )

    def get(self, institution_account_id: str) -> Credentials | None:
        cursor = self._executor.execute(
            sql="""
                SELECT institution_id, encrypted_parameters FROM credentials
                WHERE institution_account_id = :institution_account_id;
            """,
            parameters={"institution_account_id": institution_account_id},
        )

        row = cursor.fetchone()

        if row is None:
            return None


        institution_id = self._institution_registry.get_institution_id(row[0])
        encrypted_parameters = row[1]

        json_string = self._encryptor.decrypt(encrypted_parameters)
        parameters: dict[str, Any] = json.loads(json_string)

        return self._institution_registry.create_credentials(
            institution_id, institution_account_id, parameters
        )

    def remove(self, institution_account_id: str) -> None:
        self._executor.execute(
            sql="""
                DELETE FROM credentials
                WHERE institution_account_id = :institution_account_id;
            """,
            parameters={"institution_account_id": institution_account_id},
        )
