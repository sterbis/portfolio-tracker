from typing import Any

from portfolio_tracker.application.views import TransactionView

from .transaction import TransactionViewTable
from .view_table import ViewTable


VIEW_TABLE_REGISTRY: dict[type, ViewTable[Any]] = {
    TransactionView: TransactionViewTable(),
}


def get_view_table(view_cls: type[Any]) -> ViewTable[Any]:
    return VIEW_TABLE_REGISTRY[view_cls]


def get_view_table_by_name(name: str) -> ViewTable[Any]:
    for view_table in VIEW_TABLE_REGISTRY.values():
        if view_table.name == name:
            return view_table

    raise ValueError(f"View table with name '{name}' not found.")
