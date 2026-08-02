from dataclasses import dataclass, field
from typing import Callable

from filterutils import Filter

from portfolio_tracker.domain.portfolio import ConsolidationScope
from portfolio_tracker.application.shared.dtos import PortfolioValuationDto


@dataclass(frozen=True)
class GetPortfoliosQuery:
    scope: ConsolidationScope
    reporting_currency: str
    filter: Filter | None
    institution_account_ids: set[str] = field(default_factory=set)
    asset_account_ids: set[str] = field(default_factory=set)
    stream_callback: Callable[[list[PortfolioValuationDto]], None] | None = None
