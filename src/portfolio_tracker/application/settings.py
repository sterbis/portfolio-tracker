from dataclasses import dataclass, field

from portfolio_tracker.domain.portfolio import ConsolidationScope
from portfolio_tracker.domain.shared import Currency


@dataclass(frozen=True)
class MarketDataSettings:
    provider: str = "yahoo_finance"


@dataclass(frozen=True)
class ApplicationSettings:
    consolidation_scope: ConsolidationScope = ConsolidationScope.ASSET_ACCOUNT
    reporting_currency: Currency = Currency.USD
    cli_login_session_ttl: int = 3600
    market_data: MarketDataSettings = field(default_factory=MarketDataSettings)
