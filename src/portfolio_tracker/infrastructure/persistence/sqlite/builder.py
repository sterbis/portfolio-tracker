from collections.abc import Iterable
from typing import Any

from filterutils import ColumnMap, Filter, UniqueNameGenerator

from portfolio_tracker.application.shared.sort import Sort

from .registry import ColumnReference, FieldReference, Model, SchemaResolver


class SqliteStatementBuilder:
    def __init__(self, resolver: SchemaResolver) -> None:
        self._resolver = resolver

    def insert(
        self, model: Model, values: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        table = self._resolver.get_table_name(model)
        parameters = self._values_to_parameters(model, values)
        columns = parameters.keys()

        sql = f"""
            INSERT INTO {table} ({", ".join(columns)})
            VALUES ({", ".join(f":{column}" for column in columns)});
        """

        return sql, parameters

    def insert_on_conflict_do_nothing(
        self,
        model: Model,
        values: dict[str, Any],
        conflict_field_names: Iterable[str],
    ) -> tuple[str, dict[str, Any]]:
        table_name = self._resolver.get_table_name(model)
        parameters = self._values_to_parameters(model, values)

        insert_column_names = parameters.keys()
        conflict_column_names = [
            self._field_to_column_name(model, field_name)
            for field_name in conflict_field_names
        ]

        sql = f"""
            INSERT INTO {table_name} ({", ".join(insert_column_names)})
            VALUES ({", ".join(f":{column_name}" for column_name in insert_column_names)})
            ON CONFLICT({", ".join(conflict_column_names)}) DO NOTHING;
        """

        return sql, parameters

    def select(
        self,
        model: Model,
        *,
        fields: list[FieldReference] | None = None,
        include_parents: bool = False,
        distinct: bool = False,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[str, dict[str, Any], dict[ColumnReference, list[FieldReference]]]:
        select_fields = fields or self._resolver.get_model_fields(
            model, include_parents
        )

        select_columns: dict[ColumnReference, list[FieldReference]] = {}
        for field in select_fields:
            column = self._resolver.get_column(field)
            select_columns.setdefault(column, []).append(field)

        filter_columns: dict[ColumnReference, list[FieldReference]] = {}
        if filter_:
            for filter_node in filter_.iter_children():
                if filter_node.item_type is None:
                    raise ValueError(f"Missing filter model reference. {filter_node}")

                field = FieldReference(filter_node.item_type, filter_node.field)
                column = self._resolver.get_column(field)
                filter_columns.setdefault(column, []).append(field)

        order_by_columns: dict[ColumnReference, str] = {}
        if sorts:
            for sort in sorts:
                field = FieldReference(sort.item_type, sort.field)
                column = self._resolver.get_column(field)
                order_by_columns[column] = "DESC" if sort.reverse else "ASC"

        all_columns = (
            select_columns.keys() | filter_columns.keys() | order_by_columns.keys()
        )

        root_table = self._resolver.get_table(model)
        joined_tables = {
            column.table for column in all_columns if column.table != root_table
        }

        require_join = bool(joined_tables)

        sql = "SELECT "
        parameters: dict[str, Any] = {}

        if distinct:
            sql += "DISTINCT "

        select_expressions = [
            (
                f"{column.qualified_name} AS {column.alias}"
                if require_join
                else column.name
            )
            for column in select_columns
        ]
        sql += ", ".join(select_expressions) + " "

        if require_join:
            sql += f"FROM {root_table.name} AS {root_table.alias} "

            for left_table, right_table in self._resolver.resolve_relations(
                root_table, joined_tables
            ):
                left_column, right_column = self._resolver.get_related_columns(
                    left_table, right_table
                )
                sql += (
                    f"JOIN {right_table.name} AS {right_table.alias} "
                    f"ON {left_column.qualified_name} = {right_column.qualified_name} "
                )

        else:
            sql += f"FROM {root_table.name} "

        if filter_:
            column_map: ColumnMap = {
                (field.model, field.name): (
                    column.qualified_name if require_join else column.name
                )
                for column, fields in filter_columns.items()
                for field in fields
            }
            filter_sql, filter_parameters = filter_.to_sql(column_map)
            sql += f"WHERE {filter_sql} "
            parameters.update(filter_parameters)

        if order_by_columns:
            order_by_expressions: list[str] = [
                f"{column.qualified_name if require_join else column.name} {direction}"
                for column, direction in order_by_columns.items()
            ]

            sql += f"ORDER BY {', '.join(order_by_expressions)}"

        if limit is not None:
            sql += f"LIMIT {limit} "

        if offset is not None and limit is None:
            sql += "LIMIT -1 "

        if offset is not None:
            sql += f"OFFSET {offset} "

        sql += ";"

        return sql, parameters, select_columns

    def update(
        self, model: Model, values: dict[str, Any], filter_: Filter
    ) -> tuple[str, dict[str, Any]]:
        table_name = self._resolver.get_table_name(model)
        value_parameters = self._values_to_parameters(model, values)
        value_column_names = value_parameters.keys()

        filter_sql, filter_parameters = filter_.to_sql(
            column_map=self._get_filter_column_map(filter_),
            name_generator=UniqueNameGenerator(prefix="filter"),
        )

        sql = f"""
            UPDATE {table_name}
            SET {", ".join(f"{column_name} = :{column_name}" for column_name in value_column_names)}
            WHERE {filter_sql};
        """

        parameters = value_parameters | filter_parameters
        return sql, parameters

    def delete(self, model: Model, filter_: Filter) -> tuple[str, dict[str, Any]]:
        table_name = self._resolver.get_table_name(model)
        filter_sql, filter_parameters = filter_.to_sql(
            column_map=self._get_filter_column_map(filter_)
        )

        sql = f"""
            DELETE FROM {table_name}
            WHERE {filter_sql};
        """

        return sql, filter_parameters

    def _get_filter_column_map(
        self, filter_: Filter, qualified: bool = False
    ) -> ColumnMap:
        column_map: ColumnMap = {}

        for filter_node in filter_.iter_children():
            if filter_node.item_type is None:
                raise ValueError(f"Missing filter model reference. {filter_node}")

            column_name = self._resolver.get_column_name(
                field_=FieldReference(filter_node.item_type, filter_node.field),
                qualified=qualified,
            )
            column_map[(filter_node.item_type, filter_node.field)] = column_name

        return column_map

    def _values_to_parameters(
        self,
        model: Model,
        values: dict[str, Any],
        qualified: bool = False,
    ) -> dict[str, Any]:
        return {
            self._field_to_column_name(model, field_name, qualified): value
            for field_name, value in values.items()
        }

    def _field_to_column_name(
        self, model: Model, field_name: str, qualified: bool = False
    ) -> str:
        return self._resolver.get_column_name(
            FieldReference(model, field_name), qualified=qualified
        )
