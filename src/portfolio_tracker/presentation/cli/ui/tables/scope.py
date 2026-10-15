from dataclasses import dataclass
from typing import Generic

from .spec import ColumnSpec, TableSpec, TView, text_column


@dataclass(frozen=True, kw_only=True)
class ScopeViewTableSpec(TableSpec[TView], Generic[TView]):
    institution_name: ColumnSpec = text_column("scope.institution_name", "Institution")
    connection_name: ColumnSpec = text_column(
        "scope.connection_name", "Institution Account"
    )
    account_name: ColumnSpec = text_column("scope.account_name", "Account")
