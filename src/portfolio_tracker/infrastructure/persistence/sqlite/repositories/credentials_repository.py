import json
from dataclasses import asdict
from typing import Any

from filterutils import FilterNode, Operator

from portfolio_tracker.application.encryption import Encryptor
from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import CredentialsStore
from portfolio_tracker.domain.account import InstitutionAccount
from portfolio_tracker.domain.institution import Credentials
from portfolio_tracker.infrastructure.persistence.sqlite.executor import SqliteExecutor
from portfolio_tracker.infrastructure.persistence.sqlite.registry import FieldReference


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
        json_string = json.dumps(asdict(credentials))
        encrypted_value = self._encryptor.encrypt(json_string)

        inserted = self._executor.insert_on_conflict_do_nothing(
            entity=Credentials,
            values={
                "institution_account_id": institution_account_id,
                "encrypted_value": encrypted_value,
            },
            conflict_field_names=["institution_account_id"],
        )

        if not inserted:
            self._executor.update(
                entity=Credentials,
                values={
                    "encrypted_value": encrypted_value,
                },
                filter_=FilterNode(
                    "id", Operator.EQ, institution_account_id, InstitutionAccount
                ),
            )

    def retrieve(self, institution_account_id: str) -> Credentials | None:
        references = [
            FieldReference("institution_id", Credentials),
            FieldReference("encrypted_value", Credentials),
        ]

        row = self._executor.select_one(
            entity=Credentials,
            fields=references,
            filter_=FilterNode(
                "id", Operator.EQ, institution_account_id, InstitutionAccount
            ),
        )

        if not row:
            return None

        institution_id, encrypted_value = row.unpack(*references)
        json_string = self._encryptor.decrypt(encrypted_value)
        data: dict[str, Any] = json.loads(json_string)

        return self._institution_registry.create_credentials(institution_id, data)

    def remove(self, institution_account_id: str) -> None:
        self._executor.delete(
            entity=Credentials,
            filter_=FilterNode(
                "id", Operator.EQ, institution_account_id, InstitutionAccount
            ),
        )
