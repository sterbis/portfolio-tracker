from dataclasses import dataclass, field
from typing import Literal

from filterutils import Filter


@dataclass(frozen=True)
class GetTransactionsQuery:
    reporting_currency: str
    institution_account_ids: set[str] = field(default_factory=set)
    asset_account_ids: set[str] = field(default_factory=set)
    symbols: set[str] = field(default_factory=set)
    filter: Filter | None = None
    limit: int | None = None
    offset: int | None = None
    order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None
