from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from filterutils import Filter

from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.portfolio import ScopeType
from portfolio_tracker.domain.portfolio.position import AccountingMethod
from portfolio_tracker.domain.shared import Currency

if TYPE_CHECKING:
    from portfolio_tracker.application.portfolio.query_service import PortfoliosSnapshot


@dataclass(frozen=True, kw_only=True)
class BuildPortfoliosQuery:
    reporting_currency: Currency
    as_of: date | None = None
    accounting_method: AccountingMethod


@dataclass(frozen=True, kw_only=True)
class GetCashBalancesQuery:
    reporting_currency: Currency
    as_of: date | None = None
    scope: ScopeType
    filter: Filter | None = None
    sorts: list[Sort] | None = None


@dataclass(frozen=True, kw_only=True)
class GetPortfoliosQuery:
    scope: ScopeType
    filter: Filter | None = None
    sorts: list[Sort] | None = None
    portfolios_snapshot: PortfoliosSnapshot | None = None
    build_portfolios_query: BuildPortfoliosQuery | None = None
