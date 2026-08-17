from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any

from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.fx import FxRates
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
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.domain.transaction import Transaction
from portfolio_tracker.domain.user import User

type Model = type[Any]
type TableRelation = tuple[str, str]


@dataclass(frozen=True)
class FieldReference:
    model: Model
    name: str


@dataclass(frozen=True)
class TableReference:
    name: str
    alias: str


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
class SchemaRegistry:
    tables: dict[Model, TableReference]
    relations: dict[TableRelation, tuple[str, str]] = field(default_factory=dict)
    column_names: dict[Model, dict[str, str]] = field(default_factory=dict)
    column_maps: dict[Model, dict[FieldReference, ColumnReference]] = field(
        default_factory=dict
    )


TABLES = {
    User: TableReference(name="user", alias="u"),
    InstitutionAccount: TableReference(name="institution_account", alias="ia"),
    Credentials: TableReference(name="credentials", alias="c"),
    AssetAccount: TableReference(name="asset_account", alias="aa"),
    Instrument: TableReference(name="instrument", alias="i"),
    InstrumentMetadata: TableReference(name="instrument", alias="i"),
    Bond: TableReference(name="bond", alias="b"),
    Cfd: TableReference(name="cfd", alias="cf"),
    Commodity: TableReference(name="commodity", alias="co"),
    Crypto: TableReference(name="crypto", alias="cr"),
    Etf: TableReference(name="etf", alias="e"),
    Future: TableReference(name="future", alias="f"),
    Option: TableReference(name="option", alias="o"),
    Stock: TableReference(name="stock", alias="s"),
    Transaction: TableReference(name="ledger", alias="l"),
    FxRates: TableReference(name="fx_rate", alias="fr"),
    StockSplits: TableReference(name="stock_split", alias="ss"),
}

RELATIONS = {
    ("institution_account", "user"): ("user_id", "id"),
    ("credentials", "institution_account"): (
        "institution_account_id",
        "id",
    ),
    ("asset_account", "institution_account"): (
        "institution_account_id",
        "id",
    ),
    ("transaction", "asset_account"): ("asset_account_id", "id"),
    ("transaction", "instrument"): ("instrument_id", "id"),
    ("bond", "instrument"): ("id", "id"),
    ("cfd", "instrument"): ("id", "id"),
    ("commodity", "instrument"): ("id", "id"),
    ("crypto", "instrument"): ("id", "id"),
    ("etf", "instrument"): ("id", "id"),
    ("future", "instrument"): ("id", "id"),
    ("option", "instrument"): ("id", "id"),
    ("stock", "instrument"): ("id", "id"),
}

COLUMN_MAPS = {
    FxRates: {
        FieldReference(FxRates, "effective_on"): ColumnReference(
            TABLES[FxRates], "effective_on"
        ),
        FieldReference(FxRates, "base_currency"): ColumnReference(
            TABLES[FxRates], "base_currency"
        ),
        FieldReference(FxRates, "quote_currency"): ColumnReference(
            TABLES[FxRates], "quote_currency"
        ),
        FieldReference(FxRates, "rate"): ColumnReference(TABLES[FxRates], "rate"),
    },
    StockSplits: {
        FieldReference(StockSplits, "instrument_id"): ColumnReference(
            TABLES[StockSplits], "instrument_id"
        ),
        FieldReference(StockSplits, "executed_at"): ColumnReference(
            TABLES[StockSplits], "executed_at"
        ),
        FieldReference(StockSplits, "ratio"): ColumnReference(
            TABLES[StockSplits], "ratio"
        ),
    },
}

SCHEMA_REGISTRY = SchemaRegistry(
    tables=TABLES,
    relations=RELATIONS,
    column_maps=COLUMN_MAPS,
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


class SchemaResolver:
    def __init__(self, registry: SchemaRegistry):
        self._registry = registry
        self._relation_graph = TableRelationGraph(self._registry.relations)
        self._column_map: dict[FieldReference, ColumnReference] = (
            self._build_column_map()
        )

    def _build_column_map(self) -> dict[FieldReference, ColumnReference]:
        columns: dict[tuple[Model, str], ColumnReference] = {}
        column_map: dict[FieldReference, ColumnReference] = {}

        for model in self._registry.tables:
            if model in self._registry.column_maps:
                column_map.update(self._registry.column_maps[model])
                continue

            for field_object in fields(model):
                field_name = field_object.name
                if field_name.startswith("_"):
                    continue

                owner_model = self._resolve_owner_model(model, field_name)

                if (owner_model, field_name) in columns:
                    column = columns[(owner_model, field_name)]

                else:
                    table = self._registry.tables[owner_model]
                    column_name = self._registry.column_names.get(owner_model, {}).get(
                        field_name, field_name
                    )
                    column = ColumnReference(table, column_name)
                    columns[(owner_model, field_name)] = column

                field_ = FieldReference(model, field_name)
                column_map[field_] = column

        return column_map

    def _resolve_owner_model(self, model: Model, field_name: str) -> Model:
        if self._is_primary_key_field(model, field_name):
            return model

        field_declared = False
        for cls in reversed(model.__mro__):
            if not is_dataclass(cls):
                continue

            if not field_declared and field_name in cls.__annotations__:
                field_declared = True

            if field_declared and cls in self._registry.tables:
                return cls

        raise ValueError(
            f"'{field_name}' field not found in {model.__name__} inheritance chain."
        )

    def _is_primary_key_field(self, _: Model, field_name: str) -> bool:
        return field_name == "id"

    def get_table(self, model: Model) -> TableReference:
        return self._registry.tables[model]

    def get_table_name(self, model: Model) -> str:
        return self._registry.tables[model].name

    def get_column(self, field_: FieldReference) -> ColumnReference:
        return self._column_map[field_]

    def get_column_name(self, field_: FieldReference, qualified: bool = True) -> str:
        column = self._column_map[field_]
        return column.qualified_name if qualified else column.name

    def get_related_columns(
        self, left_table: TableReference, right_table: TableReference
    ) -> tuple[ColumnReference, ColumnReference]:
        left_column_name, right_column_name = self._registry.relations.get(
            (left_table.name, right_table.name), (None, None)
        )

        if not left_column_name and not right_column_name:
            right_column_name, left_column_name = self._registry.relations.get(
                (right_table.name, left_table.name), (None, None)
            )

        if not left_column_name or not right_column_name:
            raise ValueError(
                f"Missing relation between {left_table} and {right_table} table."
            )

        return ColumnReference(left_table, left_column_name), ColumnReference(
            right_table, right_column_name
        )

    def get_model_fields(
        self, model: Model, include_parents: bool = True
    ) -> list[FieldReference]:
        if model in self._registry.column_maps:
            return list(self._registry.column_maps[model])

        return [
            FieldReference(model, field_.name)
            for field_ in fields(model)
            if include_parents or self._resolve_owner_model(model, field_.name) == model
        ]

    def resolve_relations(
        self,
        table: TableReference,
        joined_tables: set[TableReference],
    ) -> list[tuple[TableReference, TableReference]]:
        tables = {table.name: table for table in {table} | joined_tables}
        relations = self._relation_graph.resolve_relations(
            table.name, {joined_table.name for joined_table in joined_tables}
        )
        return [(tables[relation[0]], tables[relation[1]]) for relation in relations]
