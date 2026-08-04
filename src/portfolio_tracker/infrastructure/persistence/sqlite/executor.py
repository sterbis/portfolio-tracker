import logging
import sqlite3
from collections.abc import Iterable
from pprint import pformat
from typing import Any

import sqlparse
from filterutils import Filter

from portfolio_tracker.application.persistence import OrderBy

from .builder import SqliteStatementBuilder
from .registry import ColumnReference, Entity, FieldReference

logger = logging.getLogger(__name__)


class Row(dict[FieldReference, Any]):
    def unpack(self, *references: FieldReference) -> tuple[Any, ...]:
        return tuple(self[reference] for reference in references)


class SqliteExecutor:
    def __init__(
        self, connection: sqlite3.Connection, builder: SqliteStatementBuilder
    ) -> None:
        self._connection = connection
        self._builder = builder

    def _log_sql(self, sql: str, parameters: dict[str, Any] | None) -> None:
        formatted_sql = sqlparse.format(
            sql, reindent=True, keyword_case="upper", indent_width=2
        )
        args = [formatted_sql]

        message = "Executing SQL:\n%s\n"
        if parameters:
            message += "\nParameters:\n%s"
            args.append(pformat(parameters, indent=2))

        logger.debug(message, *args)

    def execute(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
    ) -> sqlite3.Cursor:
        self._log_sql(sql, parameters)
        return self._connection.execute(sql, parameters or ())

    def insert(
        self, entity: Entity, values: dict[str, Any]
    ) -> sqlite3.Cursor:
        sql, parameters = self._builder.insert(entity, values)
        return self.execute(sql, parameters)

    def insert_on_conflict_do_nothing(
        self,
        entity: Entity,
        values: dict[str, Any],
        conflict_field_names: Iterable[str],
    ) -> bool:
        sql, parameters = self._builder.insert_on_conflict_do_nothing(
            entity, values, conflict_field_names
        )
        cursor = self.execute(sql, parameters)
        return cursor.rowcount > 0

    def update(
        self, entity: Entity, values: dict[str, Any], filter_: Filter
    ) -> sqlite3.Cursor:
        sql, parameters = self._builder.update(entity, values, filter_)
        return self.execute(sql, parameters)

    def delete(self, entity: Entity, filter_: Filter) -> sqlite3.Cursor:
        sql, parameters = self._builder.delete(entity, filter_)
        return self.execute(sql, parameters)

    def select(
        self,
        entity: Entity,
        *,
        fields: list[FieldReference] | None = None,
        distinct: bool = False,
        filter_: Filter | None = None,
        order_by_list: list[OrderBy] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Row]:
        sql, parameters, column_map = self._builder.select(
            entity,
            fields=fields,
            distinct=distinct,
            filter_=filter_,
            order_by_list=order_by_list,
            limit=limit,
            offset=offset,
        )
        rows = self.execute(sql, parameters).fetchall()
        return [self._remap_row(row, column_map) for row in rows]

    def select_one(
        self,
        entity: Entity,
        *,
        fields: list[FieldReference] | None = None,
        distinct: bool = False,
        filter_: Filter | None = None,
        order_by_list: list[OrderBy] | None = None,
        offset: int | None = None,
    ) -> Row | None:
        rows: list[Row] = self.select(
            entity,
            fields=fields,
            distinct=distinct,
            filter_=filter_,
            order_by_list=order_by_list,
            limit=1,
            offset=offset,
        )
        if not rows:
            return None

        return rows[0]

    def _remap_row(
        self, row: tuple[Any, ...], column_map: dict[ColumnReference, list[FieldReference]]
    ) -> Row:
        remapped_row = Row()
        for column, value in zip(column_map.keys(), row):
            for field in column_map[column]:
                remapped_row[field] = value

        return remapped_row
