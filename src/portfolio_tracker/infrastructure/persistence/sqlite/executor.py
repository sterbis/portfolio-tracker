import logging
import sqlite3
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field, is_dataclass
from pprint import pformat
from typing import Any

import sqlparse
from filterutils import ColumnMap, Filter, FilterNode, FilterTree, UniqueNameGenerator

from portfolio_tracker.application.persistence import OrderBy
from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.instrument import Instrument, Stock
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.transaction import Transaction
from portfolio_tracker.domain.user import User

logger = logging.getLogger(__name__)


EntityReference = type
EntityRelation = tuple[EntityReference, EntityReference]


@dataclass(frozen=True)
class FieldReference:
    field: str
    entity_reference: EntityReference


class EntityRelationGraph:
    def __init__(self, relations: Iterable[EntityRelation]):
        self.relations = relations
        self.related_entities: dict[type, set[type]] = {}

        for left_entity, right_entity in self.relations:
            self.related_entities.setdefault(left_entity, set()).add(right_entity)
            self.related_entities.setdefault(right_entity, set()).add(left_entity)

    def find_relation_path(self, start_entity: type, target_entity: type) -> list[type]:
        if start_entity == target_entity:
            return [start_entity]

        if target_entity not in self.related_entities:
            raise ValueError(
                f"Entity '{target_entity.__name__}' is not registered in relations graph."
            )

        queue: deque[list[type]] = deque([[start_entity]])
        visited: set[type] = {start_entity}

        while queue:
            path = queue.popleft()
            current_entity = path[-1]

            if current_entity == target_entity:
                return path

            for related_entity in self.related_entities.get(current_entity, []):
                if related_entity not in visited:
                    visited.add(related_entity)
                    new_path = list(path)
                    new_path.append(related_entity)
                    queue.append(new_path)

        raise ValueError(
            "No valid relation path found between "
            f"'{start_entity.__name__}' and '{target_entity.__name__}'."
        )

    def resolve_relation_chain(
        self, start_entity: type, target_entities: set[type]
    ) -> list[EntityRelation]:
        visited_entities: set[type] = {start_entity}
        relations: list[EntityRelation] = []

        for target_entity in target_entities:
            if target_entity in visited_entities:
                continue

            path = self.find_relation_path(start_entity, target_entity)

            for i in range(len(path) - 1):
                left_entity, right_entity = path[i], path[i + 1]
                relation = (left_entity, right_entity)

                if right_entity not in visited_entities:
                    relations.append(relation)
                    visited_entities.add(right_entity)

        return relations


@dataclass(frozen=True)
class SchemaMap:
    tables: dict[EntityReference, tuple[str, str]]
    relations: dict[EntityRelation, tuple[str, str]] = field(default_factory=dict)
    columns: dict[EntityReference, dict[str, str]] = field(default_factory=dict)


PORTFOLIO_TRACKER_SCHEMA_MAP = SchemaMap(
    tables={
        User: ("user", "u"),
        InstitutionAccount: ("institution_account", "ia"),
        AssetAccount: ("asset_account", "aa"),
        Instrument: ("instrument", "i"),
        Stock: ("stock", "s"),
        Transaction: ("ledger", "l"),
        FxRates: ("fx_rate", "fr"),
        StockSplits: ("stock_split", "ss"),
    },
    relations={
        (InstitutionAccount, User): ("user_id", "id"),
        (AssetAccount, InstitutionAccount): ("institution_account_id", "id"),
        (Transaction, AssetAccount): ("asset_account_id", "id"),
        (Transaction, Instrument): ("instrument_id", "id"),
        (Stock, Instrument): ("id", "id"),
    },
    columns={
        User: {"id": "user_id"},
        InstitutionAccount: {"id": "institution_account_id"},
        AssetAccount: {"id": "asset_account_id"},
        Instrument: {"id": "instrument_id"},
        Stock: {"id": "instrument_id"},
        Transaction: {"id": "transaction_id"},
    },
)


class SchemaMapper:
    def __init__(self, map_: SchemaMap):
        self._map = map_

    def get_table_name(self, reference: EntityReference) -> str:
        return self._map.tables[reference][0]

    def get_table_alias(self, reference: EntityReference) -> str:
        return self._map.tables[reference][1]

    def get_column_name(self, reference: FieldReference, qualified: bool = True) -> str:
        column_name = self._map.columns.get(reference.entity_reference, {}).get(
            reference.field, reference.field
        )

        if qualified:
            table_alias = self.get_table_alias(reference.entity_reference)
            return f"{table_alias}.{column_name}"

        return column_name

    def get_column_alias(self, reference: FieldReference) -> str:
        table_name = self.get_table_name(reference.entity_reference)
        column_name = self.get_column_name(reference, qualified=False)
        return f"{table_name}_{column_name}"

    def get_relation_field_references(
        self, relation: EntityRelation
    ) -> tuple[FieldReference, FieldReference]:
        left_entity_reference, right_entity_reference = relation

        left_field, right_field = self._map.relations.get(
            (left_entity_reference, right_entity_reference), (None, None)
        )

        if not left_field and not right_field:
            right_field, left_field = self._map.relations.get(
                (right_entity_reference, left_entity_reference), (None, None)
            )

        if not left_field or not right_field:
            raise ValueError(
                f"Missing relation between {left_entity_reference.__name__} "
                f"and {right_entity_reference.__name__} entities."
            )

        return FieldReference(left_field, left_entity_reference), FieldReference(
            right_field, right_entity_reference
        )

    def get_entity_field_references(
        self, entity_reference: EntityReference, include_parent_fields: bool = True
    ) -> list[FieldReference]:
        field_map: dict[str, EntityReference] = {}

        for cls in entity_reference.__mro__:
            if not is_dataclass(cls):
                continue

            for field_ in cls.__annotations__:
                if not field_.startswith("_"):
                    field_map[field_] = cls

        return [
            FieldReference(field_, cls)
            for field_, cls in field_map.items()
            if include_parent_fields or cls == entity_reference
        ]


class StatementBuilder:
    def __init__(self, mapper: SchemaMapper, graph: EntityRelationGraph) -> None:
        self._mapper = mapper
        self._graph = graph

    def insert(
        self, entity_reference: EntityReference, values: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        table = self._mapper.get_table_name(entity_reference)
        parameters = self._values_to_parameters(entity_reference, values)
        columns = parameters.keys()

        sql = f"""
            INSERT INTO {table} ({", ".join(columns)})
            VALUES ({", ".join(f":{column}" for column in columns)});
        """

        return sql, parameters

    def insert_on_conflict_do_nothing(
        self,
        entity_reference: EntityReference,
        values: dict[str, Any],
        conflict_fields: Iterable[str],
    ) -> tuple[str, dict[str, Any]]:
        table = self._mapper.get_table_name(entity_reference)
        parameters = self._values_to_parameters(entity_reference, values)
        columns = parameters.keys()
        conflict_columns = [
            self._field_to_column(field, entity_reference) for field in conflict_fields
        ]

        sql = f"""
            INSERT INTO {table} ({", ".join(columns)})
            VALUES ({", ".join(f":{column}" for column in columns)})
            ON CONFLICT({", ".join(conflict_columns)}) DO NOTHING;
        """

        return sql, parameters

    def select(
        self,
        entity_reference: EntityReference,
        *,
        field_references: list[FieldReference] | None = None,
        include_parent_fields: bool = False,
        distinct: bool = False,
        filter_: Filter | None = None,
        order_by_list: list[OrderBy] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[str, dict[str, Any], list[FieldReference]]:
        if not field_references:
            field_references = self._mapper.get_entity_field_references(
                entity_reference, include_parent_fields
            )

        joined_entity_references = self._get_joined_entity_references(
            entity_reference,
            field_references=field_references,
            filter_=filter_,
            order_by_list=order_by_list,
        )

        require_join = bool(joined_entity_references)

        sql = "SELECT "
        parameters: dict[str, Any] = {}

        if distinct:
            sql += "DISTINCT "

        select_columns: list[str] = []
        for reference in field_references:
            column = self._mapper.get_column_name(reference, qualified=require_join)
            if require_join:
                alias = self._mapper.get_column_alias(reference)
                column = f"{column} AS {alias}"

            select_columns.append(column)

        sql += ", ".join(select_columns) + " "

        sql += f"FROM {self._mapper.get_table_name(entity_reference)} "

        if require_join:
            sql += f"AS {self._mapper.get_table_alias(entity_reference)} "

            for relation in self._graph.resolve_relation_chain(
                entity_reference, joined_entity_references
            ):
                joined_entity_reference = relation[1]
                table = self._mapper.get_table_name(joined_entity_reference)
                alias = self._mapper.get_table_alias(joined_entity_reference)

                left_reference, right_reference = (
                    self._mapper.get_relation_field_references(relation)
                )
                left_column = self._mapper.get_column_name(left_reference)
                right_column = self._mapper.get_column_name(right_reference)

                sql += f"JOIN {table} AS {alias} ON {left_column} = {right_column} "

        if filter_:
            filter_sql, filter_parameters = filter_.to_sql(
                column_map=self._get_filter_column_map(filter_, qualified=require_join)
            )

            sql += f"WHERE {filter_sql} "
            parameters.update(filter_parameters)

        if order_by_list:
            order_by_columns: list[str] = []
            for order_by in order_by_list:
                column = self._mapper.get_column_name(
                    FieldReference(order_by.field, order_by.item_type),
                    qualified=require_join,
                )
                order_by_columns.append(f"{column} {order_by.direction}")

            sql += f"ORDER BY {', '.join(order_by_columns)}"

        if limit is not None:
            sql += f"LIMIT {limit} "

        if offset is not None and limit is None:
            sql += "LIMIT -1 "

        if offset is not None:
            sql += f"OFFSET {offset} "

        sql += ";"

        return sql, parameters, field_references

    def update(
        self, entity_reference: EntityReference, values: dict[str, Any], filter_: Filter
    ) -> tuple[str, dict[str, Any]]:
        table = self._mapper.get_table_name(entity_reference)
        value_parameters = self._values_to_parameters(entity_reference, values)
        columns = value_parameters.keys()

        filter_sql, filter_parameters = filter_.to_sql(
            column_map=self._get_filter_column_map(filter_),
            name_generator=UniqueNameGenerator(prefix="filter"),
        )

        sql = f"""
            UPDATE {table}
            SET {", ".join(f"{column} = :{column}" for column in columns)}
            WHERE {filter_sql};
        """

        parameters = value_parameters | filter_parameters
        return sql, parameters

    def delete(
        self, entity_reference: EntityReference, filter_: Filter
    ) -> tuple[str, dict[str, Any]]:
        table = self._mapper.get_table_name(entity_reference)
        filter_sql, filter_parameters = filter_.to_sql(
            column_map=self._get_filter_column_map(filter_)
        )

        sql = f"""
            DELETE FROM {table}
            WHERE {filter_sql};
        """

        return sql, filter_parameters

    def _get_joined_entity_references(
        self,
        entity_reference: EntityReference,
        *,
        field_references: list[FieldReference] | None = None,
        filter_: Filter | None = None,
        order_by_list: list[OrderBy] | None = None,
    ) -> set[EntityReference]:
        entity_references: set[EntityReference] = set()

        if field_references:
            for reference in field_references:
                entity_references.add(reference.entity_reference)

        if isinstance(filter_, FilterNode) and filter_.item_type:
            entity_references.add(filter_.item_type)

        elif isinstance(filter_, FilterTree):
            entity_references.update(filter_.item_types)

        if order_by_list:
            entity_references.update(
                order_by.item_type for order_by in order_by_list if order_by.item_type
            )

        return entity_references - {entity_reference}

    def _get_filter_column_map(
        self, filter_: Filter, qualified: bool = False
    ) -> ColumnMap:
        column_map: ColumnMap = {}

        for filter_node in filter_.iter_children():
            if filter_node.item_type is None:
                raise ValueError(f"Missing filter entity reference. {filter_node}")

            column = self._mapper.get_column_name(
                reference=FieldReference(filter_node.field, filter_node.item_type),
                qualified=qualified,
            )
            column_map[(filter_node.item_type, filter_node.field)] = column

        return column_map

    def _values_to_parameters(
        self,
        entity_reference: EntityReference,
        values: dict[str, Any],
        qualified: bool = False,
    ) -> dict[str, Any]:
        return {
            self._field_to_column(field, entity_reference, qualified): value
            for field, value in values.items()
        }

    def _field_to_column(
        self, field_: str, entity_reference: EntityReference, qualified: bool = False
    ) -> str:
        return self._mapper.get_column_name(
            FieldReference(field_, entity_reference), qualified=qualified
        )


class SqliteExecutor:
    def __init__(
        self, connection: sqlite3.Connection, builder: StatementBuilder
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
        self, entity_reference: EntityReference, values: dict[str, Any]
    ) -> sqlite3.Cursor:
        sql, parameters = self._builder.insert(entity_reference, values)
        return self.execute(sql, parameters)

    def insert_on_conflict_do_nothing(
        self,
        entity_reference: EntityReference,
        values: dict[str, Any],
        conflict_fields: Iterable[str],
    ) -> bool:
        sql, parameters = self._builder.insert_on_conflict_do_nothing(
            entity_reference, values, conflict_fields
        )
        cursor = self.execute(sql, parameters)
        return cursor.rowcount > 0

    def update(
        self, entity_reference: EntityReference, values: dict[str, Any], filter_: Filter
    ) -> sqlite3.Cursor:
        sql, parameters = self._builder.update(entity_reference, values, filter_)
        return self.execute(sql, parameters)

    def delete(
        self, entity_reference: EntityReference, filter_: Filter
    ) -> sqlite3.Cursor:
        sql, parameters = self._builder.delete(entity_reference, filter_)
        return self.execute(sql, parameters)

    def select(
        self,
        entity_reference: EntityReference,
        *,
        field_references: list[FieldReference] | None = None,
        distinct: bool = False,
        filter_: Filter | None = None,
        order_by_list: list[OrderBy] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[FieldReference, Any]]:
        sql, parameters, field_references = self._builder.select(
            entity_reference,
            field_references=field_references,
            distinct=distinct,
            filter_=filter_,
            order_by_list=order_by_list,
            limit=limit,
            offset=offset,
        )
        rows = self.execute(sql, parameters).fetchall()
        return [dict(zip(field_references, row)) for row in rows]

    def select_one(
        self,
        entity_reference: EntityReference,
        *,
        field_references: list[FieldReference] | None = None,
        distinct: bool = False,
        filter_: Filter | None = None,
        order_by_list: list[OrderBy] | None = None,
        offset: int | None = None,
    ) -> dict[FieldReference, Any] | None:
        rows: list[dict[FieldReference, Any]] = self.select(
            entity_reference,
            field_references=field_references,
            distinct=distinct,
            filter_=filter_,
            order_by_list=order_by_list,
            limit=1,
            offset=offset,
        )
        if not rows:
            return None

        return rows[0]
