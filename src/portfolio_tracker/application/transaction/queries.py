from dataclasses import dataclass, field

from filterutils import Filter

from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.shared import Currency


@dataclass(frozen=True, kw_only=True)
class GetTransactionsQuery:
    institution_account_ids: set[str] = field(default_factory=set)
    asset_account_ids: set[str] = field(default_factory=set)
    reporting_currency: Currency
    filter: Filter | None = None
    sorts: list[Sort] | None = None
    limit: int | None = None
    offset: int | None = None
