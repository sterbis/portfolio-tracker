import json
import sqlite3
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
                INSERT INTO credentials (institution_id, institution_connection_id, encrypted_parameters)
                VALUES (:institution_id, :institution_connection_id, :encrypted_parameters)
                ON CONFLICT(institution_connection_id) DO UPDATE SET
                encrypted_parameters = EXCLUDED.encrypted_parameters;
            """,
            parameters={
                "institution_id": credentials.institution_id,
                "institution_connection_id": credentials.institution_connection_id,
                "encrypted_parameters": encrypted_parameters,
            },
        )

    def get(self, institution_connection_id: str) -> Credentials | None:
        cursor = self._executor.execute(
            sql="""
                SELECT institution_id, institution_connection_id, encrypted_parameters
                FROM credentials
                WHERE institution_connection_id = :institution_connection_id;
            """,
            parameters={"institution_connection_id": institution_connection_id},
        )

        row = cursor.fetchone()
        if row is None:
            return None

        return self._row_to_credentials(row)

    def get_by_ids(self, institution_connection_ids: set[str]) -> list[Credentials]:
        parameters = {
            f"institution_connection_id_{index}": institution_connection_id
            for index, institution_connection_id in enumerate(
                institution_connection_ids, start=1
            )
        }
        cursor = self._executor.execute(
            sql=f"""
                SELECT institution_id, institution_connection_id, encrypted_parameters
                FROM credentials
                WHERE institution_connection_id IN ({", ".join(f":{parameter}" for parameter in parameters)});
            """,
            parameters=parameters,
        )
        return [self._row_to_credentials(row) for row in cursor.fetchall()]

    def _row_to_credentials(self, row: sqlite3.Row) -> Credentials:
        institution_id = self._institution_registry.get_institution_id(row[0])
        institution_connection_id = row[1]
        encrypted_parameters = row[2]

        json_string = self._encryptor.decrypt(encrypted_parameters)
        parameters: dict[str, Any] = json.loads(json_string)
        return self._institution_registry.create_credentials(
            institution_id, institution_connection_id, parameters
        )

    def remove(self, institution_connection_id: str) -> None:
        self._executor.execute(
            sql="""
                DELETE FROM credentials
                WHERE institution_connection_id = :institution_connection_id;
            """,
            parameters={"institution_connection_id": institution_connection_id},
        )
