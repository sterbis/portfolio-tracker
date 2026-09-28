from dataclasses import dataclass, field

from portfolio_tracker.domain.portfolio import ScopeType
from portfolio_tracker.domain.portfolio.position import AccountingMethod
from portfolio_tracker.domain.shared import Currency


@dataclass(frozen=True)
class MarketDataSettings:
    provider: str = "yahoo_finance"


@dataclass(frozen=True)
class ApplicationSettings:
    consolidation_scope: ScopeType = ScopeType.ACCOUNT
    accounting_method: AccountingMethod = AccountingMethod.AVERAGE_COST
    reporting_currency: Currency = Currency.USD
    cli_login_session_ttl: int = 3600
    market_data: MarketDataSettings = field(default_factory=MarketDataSettings)
