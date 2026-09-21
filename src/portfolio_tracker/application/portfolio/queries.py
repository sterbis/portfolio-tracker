from dataclasses import dataclass, field

from filterutils import Filter

from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.portfolio import ScopeType
from portfolio_tracker.domain.shared import Currency


@dataclass(frozen=True, kw_only=True)
class GetPortfoliosQuery:
    institution_connection_ids: set[str] = field(default_factory=set)
    account_ids: set[str] = field(default_factory=set)
    scope: ScopeType
    reporting_currency: Currency
    filter: Filter | None = None
    sorts: list[Sort] | None = None
