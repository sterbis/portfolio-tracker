from dataclasses import dataclass, field

from portfolio_tracker.domain.portfolio import ScopeType
from portfolio_tracker.domain.portfolio.position import AccountingMethod
from portfolio_tracker.domain.shared import Currency


@dataclass(frozen=True)
class MarketDataSettings:
    provider: str = "yahoo_finance"
    refresh_interval: int = 60 * 15


@dataclass(frozen=True)
class ApplicationSettings:
    consolidation_scope_type: ScopeType = ScopeType.ACCOUNT
    accounting_method: AccountingMethod = AccountingMethod.AVERAGE_COST
    reporting_currency: Currency = Currency.USD
    cli_session_ttl: int = 60 * 60
    gui_session_ttl: int = 69 * 60
    gui_session_touch_interval: int = 15 * 60
    market_data: MarketDataSettings = field(default_factory=MarketDataSettings)
