from typing import Any

from portfolio_tracker.application.views import (
    AssetAccountView,
    CashBalanceRowView,
    InstitutionConnectionView,
    PositionRowView,
    TransactionView,
)

from .account import AssetAccountViewTableSpec
from .cash_balance import CashBalanceRowViewTableSpec
from .connection import InstitutionConnectionViewTableSpec
from .position import PositionRowViewTableSpec
from .spec import TableSpec
from .transaction import TransactionViewTableSpec

TABLE_SPEC_REGISTRY: dict[type, TableSpec[Any]] = {
    AssetAccountView: AssetAccountViewTableSpec(),
    CashBalanceRowView: CashBalanceRowViewTableSpec(),
    PositionRowView: PositionRowViewTableSpec(),
    InstitutionConnectionView: InstitutionConnectionViewTableSpec(),
    TransactionView: TransactionViewTableSpec(),
}


def get_table_spec(view_cls: type[Any]) -> TableSpec[Any]:
    return TABLE_SPEC_REGISTRY[view_cls]


def get_table_spec_by_name(name: str) -> TableSpec[Any]:
    for spec in TABLE_SPEC_REGISTRY.values():
        if spec.name == name:
            return spec

    raise ValueError(f"Table specification with name '{name}' not found.")
