from dataclasses import dataclass, field

from filterutils import Filter

from portfolio_tracker.domain.portfolio import ConsolidationScope
from portfolio_tracker.domain.shared import Currency


@dataclass(frozen=True, kw_only=True)
class GetPortfoliosQuery:
    institution_account_ids: set[str] = field(default_factory=set)
    asset_account_ids: set[str] = field(default_factory=set)
    scope: ConsolidationScope
    reporting_currency: Currency
    filter: Filter | None = None
