from typing import Any

from filterutils import Filter, FilterNode, FilterTree, Operator

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import InstitutionConnectionRepository
from portfolio_tracker.application.shared.errors import (
    InstitutionConnectionNotFoundError,
)
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.institution import InstitutionConnection
from portfolio_tracker.infrastructure.persistence.sqlite.executor import SqliteExecutor
from portfolio_tracker.infrastructure.persistence.sqlite.registry import FieldReference


class SqliteInstitutionConnectionRepository(InstitutionConnectionRepository):
    def __init__(
        self,
        user_id: str,
        executor: SqliteExecutor,
        institution_registry: InstitutionRegistry,
    ) -> None:
        super().__init__(user_id)
        self._executor = executor
        self._institution_registry = institution_registry
        self._scope_filter = FilterNode(
            "user_id", Operator.EQ, self._user_id, InstitutionConnection
        )

    def add(self, connection: InstitutionConnection) -> None:
        if connection.user_id != self._user_id:
            raise InstitutionConnectionNotFoundError(connection.id)

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
            filter_=FilterTree.and_combine(filter_, self._scope_filter),
            sorts=sorts,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_institution_connection(row) for row in rows]

    def get_by_id(self, connection_id: str) -> InstitutionConnection | None:
        connections = self.get(
            filter_=FilterNode("id", Operator.EQ, connection_id, InstitutionConnection),
        )
        return connections[0] if connections else None

    def get_by_ids(self, connection_ids: set[str]) -> list[InstitutionConnection]:
        if not connection_ids:
            return []

        return self.get(
            filter_=FilterNode("id", Operator.IN, connection_ids, InstitutionConnection)
        )

    def get_by_user_id(self, user_id: str) -> list[InstitutionConnection]:
        return self.get()

    def update(self, connection: InstitutionConnection) -> int:
        if connection.user_id != self._user_id:
            raise InstitutionConnectionNotFoundError(connection.id)

        cursor = self._executor.update(
            model=InstitutionConnection,
            values=self._institution_connection_to_values(connection),
            filter_=FilterTree(
                FilterNode("id", Operator.EQ, connection.id, InstitutionConnection),
                self._scope_filter,
            ),
        )
        return cursor.rowcount

    def remove_by_id(self, connection_id: str) -> int:
        cursor = self._executor.delete(
            model=InstitutionConnection,
            filter_=FilterTree(
                FilterNode("id", Operator.EQ, connection_id, InstitutionConnection),
                self._scope_filter,
            ),
        )
        return cursor.rowcount

    def _institution_connection_to_values(
        self, connection: InstitutionConnection
    ) -> dict[str, Any]:
        return {
            "id": connection.id,
            "institution_id": connection.institution_id,
            "user_id": connection.user_id,
            "name": connection.name,
            "sync_from": connection.sync_from,
            "last_synced_at": connection.last_synced_at,
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
            sync_from=row[field("sync_from")],
            last_synced_at=row[field("last_synced_at")],
        )
