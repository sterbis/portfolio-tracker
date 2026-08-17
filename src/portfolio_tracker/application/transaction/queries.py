from dataclasses import dataclass, field

from filterutils import Filter

from portfolio_tracker.application.shared.order_by import OrderBy


@dataclass(frozen=True)
class GetTransactionsQuery:
    reporting_currency: str
    institution_account_ids: set[str] = field(default_factory=set)
    asset_account_ids: set[str] = field(default_factory=set)
    symbols: set[str] = field(default_factory=set)
    filter: Filter | None = None
    limit: int | None = None
    offset: int | None = None
    order_by_list: list[OrderBy] | None = None
