from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Literal

from filterutils import Filter

from portfolio_tracker.domain.portfolio import ConsolidationScope

from .dtos import PortfolioValuationDto


@dataclass(frozen=True)
class GetAccountOverviewQuery:
    user_id: str


class OutputType(Enum):
    PORTFOLIO = auto()
    PORTFOLIO_VALUATION = auto()
    VALUED_PORTFOLIO = auto()


@dataclass(frozen=True)
class GetPortfoliosQuery:
    scope: ConsolidationScope
    reporting_currency: str
    filter: Filter
    output_type: OutputType = OutputType.VALUED_PORTFOLIO
    stream_callback: Callable[[list[PortfolioValuationDto]], None] | None = None


@dataclass(frozen=True)
class GetTransactionsQuery:
    reporting_currency: str
    filter: Filter
    limit: int | None = None
    offset: int | None = None
    order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = [("executed_at", "ASC")]
