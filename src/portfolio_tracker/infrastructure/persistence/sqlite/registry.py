from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any

from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.institution import Credentials
from portfolio_tracker.domain.instrument import (
    Bond,
    Cfd,
    Commodity,
    Crypto,
    Etf,
    Future,
    Instrument,
    InstrumentMetadata,
    Option,
    Stock,
)
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.transaction import Transaction
from portfolio_tracker.domain.user import User

type Entity = type[Any]
type EntityRelation = tuple[Entity, Entity]


@dataclass(frozen=True)
class FieldReference:
    entity: Entity
    name: str


@dataclass(frozen=True)
class TableReference:
    name: str
    alias: str


type TableRelation = tuple[str, str]


@dataclass(frozen=True)
class ColumnReference:
    table: TableReference
    name: str

    @property
    def qualified_name(self) -> str:
        return f"{self.table.alias}.{self.name}"

    @property
    def alias(self) -> str:
        return f"{self.table.name}_{self.name}"


@dataclass(frozen=True)
class EntityRegistry:
    entities: dict[Entity, TableReference]
    table_relations: dict[TableRelation, tuple[str, str]] = field(default_factory=dict)
    relations: dict[EntityRelation, tuple[str, str]] = field(default_factory=dict)
    fields: dict[Entity, dict[str, str]] = field(default_factory=dict)


PORTFOLIO_TRACKER_ENTITY_REGISTRY = EntityRegistry(
    entities={
        User: TableReference("user", "u"),
        InstitutionAccount: TableReference("institution_account", "ia"),
        Credentials: TableReference("credentials", "c"),
        AssetAccount: TableReference("asset_account", "aa"),
        Instrument: TableReference("instrument", "i"),
        InstrumentMetadata: TableReference("instrument", "i"),
        Bond: TableReference("bond", "b"),
        Cfd: TableReference("cfd", "cf"),
        Commodity: TableReference("commodity", "co"),
        Crypto: TableReference("crypto", "cc"),
        Etf: TableReference("etf", "e"),
        Future: TableReference("future", "f"),
        Option: TableReference("option", "o"),
        Stock: TableReference("stock", "s"),
        Transaction: TableReference("ledger", "l"),
        FxRates: TableReference("fx_rate", "fr"),
        StockSplits: TableReference("stock_split", "ss"),
    },
    table_relations={
        ("institution_account", "user"): ("user_id", "user_id"),
        ("credentials", "institution_account"): (
            "institution_account_id",
            "institution_account_id",
        ),
        ("asset_account", "institution_account"): (
            "institution_account_id",
            "institution_account",
        ),
        ("transaction", "asset_account"): ("asset_account_id", "asset_account_id"),
        ("transaction", "instrument"): ("instrument_id", "instrument_id"),
        ("bond", "instrument"): ("instrument_id", "instrument_id"),
        ("cfd", "instrument"): ("instrument_id", "instrument_id"),
        ("commodity", "instrument"): ("instrument_id", "instrument_id"),
        ("crypto", "instrument"): ("instrument_id", "instrument_id"),
        ("etf", "instrument"): ("instrument_id", "instrument_id"),
        ("future", "instrument"): ("instrument_id", "instrument_id"),
        ("option", "instrument"): ("instrument_id", "instrument_id"),
        ("stock", "instrument"): ("instrument_id", "instrument_id"),
    },
    relations={
        (InstitutionAccount, User): ("user_id", "id"),
        (Credentials, InstitutionAccount): ("institution_account_id", "id"),
        (AssetAccount, InstitutionAccount): ("institution_account_id", "id"),
        (Transaction, AssetAccount): ("asset_account_id", "id"),
        (Transaction, Instrument): ("instrument_id", "id"),
        (Bond, Instrument): ("id", "id"),
        (Cfd, Instrument): ("id", "id"),
        (Commodity, Instrument): ("id", "id"),
        (Crypto, Instrument): ("id", "id"),
        (Etf, Instrument): ("id", "id"),
        (Future, Instrument): ("id", "id"),
        (Option, Instrument): ("id", "id"),
        (Stock, Instrument): ("id", "id"),
    },
    fields={
        User: {"id": "user_id"},
        InstitutionAccount: {"id": "institution_account_id"},
        AssetAccount: {"id": "asset_account_id"},
        Instrument: {"id": "instrument_id"},
        Transaction: {"id": "transaction_id"},
    },
)


class TableRelationGraph:
    def __init__(self, relations: Iterable[TableRelation]):
        self.relations = relations
        self.related_tables: dict[str, set[str]] = {}

        for left_table, right_table in self.relations:
            self.related_tables.setdefault(left_table, set()).add(right_table)
            self.related_tables.setdefault(right_table, set()).add(left_table)

    def find_relation_path(self, start_table: str, target_table: str) -> list[str]:
        if start_table == target_table:
            return [start_table]

        if target_table not in self.related_tables:
            raise ValueError(
                f"Table '{target_table}' is not registered in relation graph."
            )

        queue: deque[list[str]] = deque([[start_table]])
        visited_tables: set[str] = {start_table}

        while queue:
            path = queue.popleft()
            current_table = path[-1]

            if current_table == target_table:
                return path

            for related_table in self.related_tables.get(current_table, []):
                if related_table not in visited_tables:
                    visited_tables.add(related_table)
                    new_path = list(path)
                    new_path.append(related_table)
                    queue.append(new_path)

        raise ValueError(
            f"No valid relation path found between '{start_table}' and '{target_table}' tables."
        )

    def resolve_relations(
        self, start_table: str, target_tables: set[str]
    ) -> list[TableRelation]:
        visited_tables: set[str] = {start_table}
        relations: list[TableRelation] = []

        for target_table in target_tables:
            if target_table in visited_tables:
                continue

            path = self.find_relation_path(start_table, target_table)

            for i in range(len(path) - 1):
                left_table, right_table = path[i], path[i + 1]
                relation = (left_table, right_table)

                if right_table not in visited_tables:
                    relations.append(relation)
                    visited_tables.add(right_table)

        return relations


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

    def resolve_relations(
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


class EntityResolver:
    def __init__(self, registry: EntityRegistry):
        self._registry = registry
        self._graph = EntityRelationGraph(self._registry.relations)
        self._table_graph = TableRelationGraph(self._registry.table_relations)
        self._column_map: dict[FieldReference, ColumnReference] = {}

        self._populate_column_map()

    def _resolve_owner_entity(self, entity: Entity, field_name: str) -> Entity:
        field_declared = False
        for cls in reversed(entity.__mro__):
            if not is_dataclass(cls):
                continue

            if not field_declared and field_name in cls.__annotations__:
                field_declared = True

            if field_declared and cls in self._registry.entities:
                return cls

        raise ValueError(
            f"'{field_name}' field not found in {entity.__name__} inheritance chain."
        )

    def _populate_column_map(self) -> None:
        columns: dict[tuple[Entity, str], ColumnReference] = {}

        for entity in self._registry.entities:
            for field_obj in fields(entity):
                field_name = field_obj.name
                if field_name.startswith("_"):
                    continue

                owner_entity = self._resolve_owner_entity(entity, field_name)

                if (owner_entity, field_name) in columns:
                    column = columns[(owner_entity, field_name)]

                else:
                    table = self._registry.entities[owner_entity]
                    column_name = self._registry.fields.get(owner_entity, {}).get(
                        field_name, field_name
                    )
                    column = ColumnReference(table, column_name)

                field_ = FieldReference(entity, field_name)
                self._column_map[field_] = column

    def get_table(self, entity: Entity) -> TableReference:
        return self._registry.entities[entity]

    def get_table_name(self, entity: Entity) -> str:
        return self._registry.entities[entity].name

    def get_table_alias(self, entity: Entity) -> str:
        return self._registry.entities[entity].alias

    def get_column(self, field_: FieldReference) -> ColumnReference:
        return self._column_map[field_]

    def get_column_name(self, field_: FieldReference, qualified: bool = True) -> str:
        column = self._column_map[field_]
        return column.qualified_name if qualified else column.name

    def get_column_alias(self, field_: FieldReference) -> str:
        return self._column_map[field_].alias

    def get_related_fields(
        self, relation: EntityRelation
    ) -> tuple[FieldReference, FieldReference]:
        left_entity, right_entity = relation

        left_field_name, right_field_name = self._registry.relations.get(
            (left_entity, right_entity), (None, None)
        )

        if not left_field_name and not right_field_name:
            right_field_name, left_field_name = self._registry.relations.get(
                (right_entity, left_entity), (None, None)
            )

        if not left_field_name or not right_field_name:
            raise ValueError(
                f"Missing relation between {left_entity.__name__} "
                f"and {right_entity.__name__} entities."
            )

        return FieldReference(left_entity, left_field_name), FieldReference(
            right_entity, right_field_name
        )

    def get_related_columns(
        self, left_table: TableReference, right_table: TableReference
    ) -> tuple[ColumnReference, ColumnReference]:
        left_column_name, right_column_name = self._registry.table_relations.get(
            (left_table.name, right_table.name), (None, None)
        )

        if not left_column_name and not right_column_name:
            right_column_name, left_column_name = self._registry.table_relations.get(
                (right_table.name, left_table.name), (None, None)
            )

        if not left_column_name or not right_column_name:
            raise ValueError(
                f"Missing relation between {left_table} and {right_table} table."
            )

        return ColumnReference(left_table, left_column_name), ColumnReference(
            right_table, right_column_name
        )

    def get_entity_fields(
        self, entity: Entity, include_parents: bool = True
    ) -> list[FieldReference]:
        field_names = (
            [field_.name for field_ in fields(entity)]
            if include_parents
            else list(entity.__annotations__)
        )
        return [FieldReference(entity, field_name) for field_name in field_names]

    def resolve_relations(
        self,
        entity_reference: Entity,
        joined_entity_references: set[Entity],
    ) -> list[EntityRelation]:
        return self._graph.resolve_relations(entity_reference, joined_entity_references)

    def resolve_table_relations(
        self,
        table: TableReference,
        joined_tables: set[TableReference],
    ) -> list[tuple[TableReference, TableReference]]:
        tables = {table.name: table for table in {table} | joined_tables}
        relations = self._table_graph.resolve_relations(
            table.name, {joined_table.name for joined_table in joined_tables}
        )
        return [(tables[relation[0]], tables[relation[1]]) for relation in relations]
