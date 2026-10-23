from dataclasses import dataclass
from datetime import date

from portfolio_tracker.application.shared.service import QueryOptions
from portfolio_tracker.domain.portfolio import ScopeType
from portfolio_tracker.domain.portfolio.position import AccountingMethod
from portfolio_tracker.domain.shared import Currency


@dataclass(frozen=True, kw_only=True)
class BuildPortfolioSnapshotQuery:
    reporting_currency: Currency
    as_of: date | None = None
    accounting_method: AccountingMethod


@dataclass(frozen=True, kw_only=True)
class ViewPortfolioSnapshotQuery:
    scope_type: ScopeType
    options: QueryOptions = QueryOptions()


@dataclass(frozen=True, kw_only=True)
class GetPositionsQuery:
    build: BuildPortfolioSnapshotQuery
    view: ViewPortfolioSnapshotQuery


@dataclass(frozen=True, kw_only=True)
class GetCashBalancesQuery:
    build: BuildPortfolioSnapshotQuery
    view: ViewPortfolioSnapshotQuery


@dataclass(frozen=True, kw_only=True)
class GetPortfolioQuery:
    build: BuildPortfolioSnapshotQuery
    view: ViewPortfolioSnapshotQuery
