from datetime import datetime, timezone
from filterutils import FilterNode, Operator

from portfolio_tracker.domain.institution import Credentials, InstitutionRegistry
from portfolio_tracker.application.ports.credentials_store import CredentialsStore
from portfolio_tracker.application.ports.encryptor import Encryptor

from portfolio_tracker.infrastructure.persistence.credentials_mapper import (
    deserialize_credentials,
    serialize_credentials,
)

from ..executor import SqliteExecutor


class SqliteCredentialsRepository(CredentialsStore):
    def __init__(
        self,
        institution_registry: InstitutionRegistry,
        encryptor: Encryptor,
        executor: SqliteExecutor,
    ) -> None:
        super().__init__(institution_registry)
        self._encryptor = encryptor
        self._executor = executor

    def store(self, institution_account_id: str, credentials: Credentials) -> None:
        plain_text = serialize_credentials(credentials)
        encrypted_text = self._encryptor.encrypt(plain_text)

        values = {
            "institution_account_id": institution_account_id,
            "encrypted_value": encrypted_text,
            "key_id": None,
            "version": 1,
            "created_on": datetime.now(tz=timezone.utc).isoformat(),
            "rotated_on": None,
        }

        inserted = self._executor.insert_if_not_exists(
            table="credentials",
            values=values,
            conflict_columns=["institution_account_id"],
        )

        if not inserted:
            update_values = {
                "encrypted_value": encrypted_text,
                "key_id": None,
                "version": 1,
                "rotated_on": None,
            }

            self._executor.update(
                table="credentials",
                values=update_values,
                filter_=FilterNode(
                    "institution_account_id", Operator.EQ, institution_account_id
                ),
            )

    def retrieve(self, institution_account_id: str) -> Credentials | None:
        cursor = self._executor.execute(
            sql="""
                SELECT c.encrypted_value, ia.institution_id
                FROM credentials c
                JOIN institution_account ia ON ia.institution_account_id = c.institution_account_id
                WHERE ia.institution_account_id = :institution_account_id;
            """,
            parameters={"institution_account_id": institution_account_id},
        )
        row = cursor.fetchone()

        if not row:
            return None

        encrypted_text = row["encrypted_value"]
        institution_id = row["institution_id"]

        institution = self._institution_registry.get(institution_id)
        plain_text = self._encryptor.decrypt(encrypted_text)
        credentials = deserialize_credentials(institution, plain_text)

        return credentials

    def remove(self, institution_account_id: str) -> None:
        self._executor.delete(
            table="credentials",
            filter_=FilterNode(
                "institution_account_id", Operator.EQ, institution_account_id
            ),
        )
