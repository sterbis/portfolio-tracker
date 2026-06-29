import logging
import sqlite3
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pprint import pformat
from typing import Any, Literal

import sqlparse
from filterutils import Filter, UniqueNameGenerator

logger = logging.getLogger(__name__)


class SqliteExecutor:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def _to_database_value(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.name
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value

    def _to_database_values(self, parameters: dict[str, Any]) -> dict[str, Any]:
        return {
            name: self._to_database_value(value) for name, value in parameters.items()
        }

    def _log_sql(self, sql: str, parameters: dict[str, Any]) -> None:
        formatted_sql = sqlparse.format(
            sql, reindent=True, keyword_case="upper", indent_width=2
        )
        logger.debug(
            "Executing SQL:\n%s\n\nParameters:\n%s",
            formatted_sql.strip(),
            pformat(parameters, indent=2),
        )

    def execute(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
    ) -> sqlite3.Cursor:
        if parameters:
            parameters = self._to_database_values(parameters)
        else:
            parameters = {}

        self._log_sql(sql, parameters)
        return self._connection.execute(sql, parameters)

    def insert(self, table: str, values: dict[str, Any]) -> sqlite3.Cursor:
        return self.execute(
            sql=f"""
                INSERT INTO {table} ({", ".join(values)})
                VALUES ({", ".join(f":{column}" for column in values)});
            """,
            parameters=values,
        )

    def insert_on_conflict(
        self,
        table: str,
        values: dict[str, Any],
        conflict_columns: Iterable[str],
    ) -> bool:
        cursor = self.execute(
            sql=f"""
                INSERT INTO {table} ({", ".join(values)})
                VALUES ({", ".join(f":{parameter}" for parameter in values)})
                ON CONFLICT({", ".join(conflict_columns)}) DO NOTHING;
            """,
            parameters=values,
        )
        return cursor.rowcount > 0

    def update(
        self, table: str, values: dict[str, Any], filter_: Filter
    ) -> sqlite3.Cursor:
        filter_sql, filter_parameters = filter_.to_sql(
            name_generator=UniqueNameGenerator(prefix="filter")
        )
        return self.execute(
            sql=f"""
                UPDATE {table} 
                SET {", ".join(f"{column} = :{column}" for column in values)}
                WHERE {filter_sql};
            """,
            parameters=values | filter_parameters,
        )

    def delete(self, table: str, filter_: Filter) -> sqlite3.Cursor:
        filter_sql, filter_parameters = filter_.to_sql()
        return self.execute(
            sql=f"""
                DELETE FROM {table}
                WHERE {filter_sql};
            """,
            parameters=filter_parameters,
        )

    def select(
        self,
        table: str,
        *,
        columns: Iterable[str] | None = None,
        distinct: bool = False,
        filter_: Filter | None = None,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[sqlite3.Row]:
        columns = ", ".join(columns) if columns else "*"
        parameters: dict[str, Any] = {}

        sql = "SELECT "
        if distinct:
            sql += "DISTINCT "

        sql += f"{columns} FROM {table} "

        if filter_:
            filter_sql, filter_parameters = filter_.to_sql()
            sql += f"WHERE {filter_sql} "
            parameters.update(filter_parameters)
        if order_by:
            sql += f"""
                ORDER BY {", ".join(f"{column} {direction}" for column, direction in order_by)}
            """
        if limit:
            sql += f"LIMIT {limit} "
        if order_by:
            sql += f"OFFSET {offset} "

        sql += ";"

        rows: list[sqlite3.Row] = self.execute(sql, parameters).fetchall()
        return rows

    def select_one(
        self,
        table: str,
        *,
        columns: Iterable[str] | None = None,
        filter_: Filter | None = None,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> sqlite3.Row | None:
        rows: list[sqlite3.Row] = self.select(
            table,
            columns=columns,
            filter_=filter_,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        if not rows:
            return None

        return rows[0]
