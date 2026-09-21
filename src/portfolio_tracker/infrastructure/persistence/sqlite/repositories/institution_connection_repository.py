from typing import Any

from filterutils import Filter, FilterNode, Operator

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import InstitutionConnectionRepository
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.institution import InstitutionConnection
from portfolio_tracker.infrastructure.persistence.sqlite.executor import SqliteExecutor
from portfolio_tracker.infrastructure.persistence.sqlite.registry import FieldReference


class SqliteInstitutionConnectionRepository(InstitutionConnectionRepository):
    def __init__(
        self, institution_registry: InstitutionRegistry, executor: SqliteExecutor
    ) -> None:
        self._institution_registry = institution_registry
        self._executor = executor

    def add(self, connection: InstitutionConnection) -> None:
        self._executor.insert(
            model=InstitutionConnection,
            values=self._institution_connection_to_values(connection),
        )

    def get(
        self,
        *,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[InstitutionConnection]:
        rows = self._executor.select(
            model=InstitutionConnection,
            filter_=filter_,
            sorts=sorts,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_institution_connection(row) for row in rows]

    def get_by_id(self, connection_id: str) -> InstitutionConnection | None:
        row = self._executor.select_one(
            model=InstitutionConnection,
            filter_=FilterNode("id", Operator.EQ, connection_id, InstitutionConnection),
        )
        return self._row_to_institution_connection(row) if row else None

    def get_by_ids(self, connection_ids: set[str]) -> list[InstitutionConnection]:
        if not connection_ids:
            return []

        return self.get(
            filter_=FilterNode("id", Operator.IN, connection_ids, InstitutionConnection)
        )

    def get_by_user_id(self, user_id: str) -> list[InstitutionConnection]:
        return self.get(
            filter_=FilterNode("user_id", Operator.EQ, user_id, InstitutionConnection)
        )

    def update(self, connection: InstitutionConnection) -> None:
        self._executor.update(
            model=InstitutionConnection,
            values=self._institution_connection_to_values(connection),
            filter_=FilterNode("id", Operator.EQ, connection.id, InstitutionConnection),
        )

    def remove_by_id(self, connection_id: str) -> None:
        self._executor.delete(
            model=InstitutionConnection,
            filter_=FilterNode("id", Operator.EQ, connection_id, InstitutionConnection),
        )

    def _institution_connection_to_values(
        self, account: InstitutionConnection
    ) -> dict[str, Any]:
        return {
            "id": account.id,
            "institution_id": account.institution_id,
            "user_id": account.user_id,
            "name": account.name,
            "account_opened_on": account.account_opened_on,
            "last_synced_at": account.last_synced_at,
        }

    def _row_to_institution_connection(
        self, row: dict[FieldReference, Any]
    ) -> InstitutionConnection:
        def field(field: str) -> FieldReference:
            return FieldReference(InstitutionConnection, field)

        return InstitutionConnection(
            id=row[field("id")],
            user_id=row[field("user_id")],
            institution_id=self._institution_registry.get_institution_id(
                row[field("institution_id")]
            ),
            name=row[field("name")],
            account_opened_on=row[field("account_opened_on")],
            last_synced_at=row[field("last_synced_at")],
        )
