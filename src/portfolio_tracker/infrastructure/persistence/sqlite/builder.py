from collections.abc import Iterable
from typing import Any

from filterutils import Filter, UniqueNameGenerator

from portfolio_tracker.application.shared.sort import Sort

from .registry import (
    ColumnReference,
    FieldReference,
    Model,
    SchemaResolver,
    TableReference,
)

FieldMap = dict[ColumnReference, list[FieldReference]]


class SqliteStatementBuilder:
    def __init__(self, resolver: SchemaResolver) -> None:
        self._resolver = resolver

    def insert(
        self, model: Model, values: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        table_name = self._resolver.get_table_name(model)
        column_name_map, parameter_name_map = self._resolve_names(model, list(values))

        column_names: list[str] = []
        parameters: dict[str, Any] = {}

        for field_name, value in values.items():
            column_names.append(column_name_map[field_name])
            parameters[parameter_name_map[field_name]] = value

        sql = f"""
            INSERT INTO {table_name} ({", ".join(column_names)})
            VALUES ({", ".join(f":{parameter_name}" for parameter_name in parameters)})
            ;
        """

        return sql, parameters

    def insert_on_conflict_do_nothing(
        self,
        model: Model,
        values: dict[str, Any],
        conflict_field_names: Iterable[str],
    ) -> tuple[str, dict[str, Any]]:
        insert_sql, parameters = self.insert(model, values)
        insert_sql = insert_sql.strip().rstrip(";")

        column_name_map, _ = self._resolve_names(model, conflict_field_names)
        conflict_column_names = [
            column_name_map[field_name] for field_name in conflict_field_names
        ]

        sql = f"""
            {insert_sql}
            ON CONFLICT({", ".join(conflict_column_names)}) DO NOTHING
            ;
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
        parameter_name_generator: UniqueNameGenerator | None = None,
    ) -> tuple[str, dict[str, Any], FieldMap]:
        fields = fields or self._resolver.get_model_fields(model, include_parents)

        root_table = self._resolver.get_table(model)

        select_columns, select_field_map = self._get_select_columns(fields)
        filter_columns, filter_field_map = self._get_filter_columns(filter_)
        order_by_columns, direction_map = self._get_order_by_columns(sorts)
        all_columns = select_columns + filter_columns + order_by_columns

        join_sql = self._join_clause(root_table, all_columns)
        qualified = bool(join_sql)
        where_sql, parameters = self._where_clause(
            model,
            filter_,
            filter_field_map,
            qualified=qualified,
            parameter_name_generator=parameter_name_generator,
        )
        order_by_sql = self._order_by_clause(direction_map, qualified)
        column_names = ", ".join(
            column.qualified_name if qualified else column.name
            for column in select_columns
        )
        distinct_sql = limit_sql = offset_sql = ""
        if distinct:
            distinct_sql = "DISTINCT "

        if limit is not None:
            limit_sql = f"LIMIT {limit} "

        if offset is not None and limit is None:
            limit_sql = "LIMIT -1 "

        if offset is not None:
            offset_sql = f"OFFSET {offset} "

        sql = f"""
            SELECT {distinct_sql} {column_names}
            FROM {root_table.name}
            {join_sql}
            {where_sql}
            {order_by_sql}
            {limit_sql}
            {offset_sql}
            ;
        """

        return sql, parameters, select_field_map

    def update(
        self, model: Model, values: dict[str, Any], filter_: Filter
    ) -> tuple[str, dict[str, Any]]:
        table_name = self._resolver.get_table_name(model)

        _, filter_field_map = self._get_filter_columns(filter_)
        where_sql, where_parameters = self._where_clause(
            model,
            filter_,
            filter_field_map,
            supports_joins=False,
            parameter_name_generator=UniqueNameGenerator(prefix="filter_parameter"),
        )
        set_sql, set_parameters = self._set_clause(model, values)

        sql = f"""
            UPDATE {table_name}
            {set_sql}
            {where_sql}
            ;
        """
        parameters = set_parameters | where_parameters

        return sql, parameters

    def delete(self, model: Model, filter_: Filter) -> tuple[str, dict[str, Any]]:
        table_name = self._resolver.get_table_name(model)
        _, filter_field_map = self._get_filter_columns(filter_)
        where_sql, parameters = self._where_clause(
            model, filter_, filter_field_map, supports_joins=False
        )

        sql = f"""
            DELETE FROM {table_name}
            {where_sql}
            ;
        """

        return sql, parameters

    def _get_select_columns(
        self, fields: list[FieldReference]
    ) -> tuple[list[ColumnReference], FieldMap]:
        field_map = self._get_field_map(fields)
        return list(field_map), field_map

    def _get_filter_columns(
        self, filter_: Filter | None
    ) -> tuple[list[ColumnReference], FieldMap]:
        if filter_ is None:
            return [], {}

        fields: list[FieldReference] = []
        for filter_node in filter_.iter_children():
            if filter_node.item_type is None:
                raise ValueError(f"Missing filter model reference. {filter_node}")

            fields.append(FieldReference(filter_node.item_type, filter_node.field))

        field_map = self._get_field_map(fields)
        return list(field_map), field_map

    def _get_field_map(self, fields: list[FieldReference]) -> FieldMap:
        field_map: FieldMap = {}
        for field in fields:
            column = self._resolver.get_column(field)
            field_map.setdefault(column, []).append(field)

        return field_map

    def _get_order_by_columns(
        self, sorts: list[Sort] | None
    ) -> tuple[list[ColumnReference], dict[ColumnReference, str]]:
        if sorts is None:
            return [], {}

        direction_map: dict[ColumnReference, str] = {}
        for sort in sorts:
            field = FieldReference(sort.item_type, sort.field)
            column = self._resolver.get_column(field)
            direction_map[column] = "DESC" if sort.reverse else "ASC"

        return list(direction_map), direction_map

    def _join_clause(
        self, root_table: TableReference, columns: list[ColumnReference]
    ) -> str:
        joined_tables = {
            column.table for column in columns if column.table != root_table
        }
        sql = ""

        for left_table, right_table in self._resolver.resolve_relations(
            root_table, joined_tables
        ):
            left_column, right_column = self._resolver.get_related_columns(
                left_table, right_table
            )
            sql += (
                f"JOIN {right_table.name} "
                f"ON {left_column.qualified_name} = {right_column.qualified_name} "
            )

        return sql

    def _where_clause(
        self,
        model: Model,
        filter_: Filter | None,
        field_map: FieldMap,
        *,
        supports_joins: bool = True,
        qualified: bool = False,
        parameter_name_generator: UniqueNameGenerator | None = None,
    ) -> tuple[str, dict[str, Any]]:
        if filter_ is None:
            return "", {}

        if not supports_joins and self._is_multi_table_filter(model, filter_):
            id_field = FieldReference(model, "id")
            subquery_sql, parameters, _ = self.select(
                model,
                fields=[id_field],
                filter_=filter_,
                parameter_name_generator=parameter_name_generator,
            )
            return f"WHERE id IN ({subquery_sql.strip().rstrip(";")})", parameters

        filter_sql, parameters = filter_.to_sql(
            column_map={
                (field.model, field.name): (
                    column.qualified_name if qualified else column.name
                )
                for column, fields in field_map.items()
                for field in fields
            },
            name_generator=parameter_name_generator,
        )
        return f"WHERE {filter_sql} ", parameters

    def _order_by_clause(
        self, direction_map: dict[ColumnReference, str], qualified: bool = False
    ) -> str:
        if not direction_map:
            return ""

        order_by_sql = ", ".join(
            f"{column.qualified_name if qualified else column.name} {direction}"
            for column, direction in direction_map.items()
        )
        return f"ORDER BY {order_by_sql} "

    def _set_clause(
        self,
        model: Model,
        values: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        column_name_map, parameter_name_map = self._resolve_names(model, list(values))

        sql = "SET "
        parameters: dict[str, Any] = {}

        for field_name, value in values.items():
            parameters[parameter_name_map[field_name]] = value
            sql += (
                f"{column_name_map[field_name]} = :{parameter_name_map[field_name]}, "
            )

        sql = sql.rstrip(", ")
        return sql, parameters

    def _resolve_names(
        self,
        model: Model,
        field_names: Iterable[str],
        qualified: bool = False,
    ) -> tuple[dict[str, str], dict[str, str]]:
        column_name_map: dict[str, str] = {}
        parameter_name_map: dict[str, str] = {}

        for field_name in field_names:
            column_name = self._resolver.get_column_name(
                FieldReference(model, field_name), qualified=qualified
            )
            parameter_name = column_name.replace(".", "_")
            column_name_map[field_name] = column_name
            parameter_name_map[field_name] = parameter_name

        return column_name_map, parameter_name_map

    def _is_multi_table_filter(self, model: Model, filter_: Filter) -> bool:
        for child_filter in filter_.iter_children():
            if child_filter.item_type != model:
                return True

        return False
