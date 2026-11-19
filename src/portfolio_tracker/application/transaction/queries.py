from dataclasses import dataclass, field


from portfolio_tracker.application.shared.service import QueryOptions
from portfolio_tracker.domain.shared import Currency


@dataclass(frozen=True, kw_only=True)
class GetTransactionsQuery:
    connection_ids: set[str] = field(default_factory=set)
    account_ids: set[str] = field(default_factory=set)
    reporting_currency: Currency
    options: QueryOptions = QueryOptions()
