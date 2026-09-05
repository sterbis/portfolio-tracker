from dataclasses import dataclass, field


@dataclass(frozen=True)
class MarketDataSettings:
    provider: str = "yahoo_finance"


@dataclass(frozen=True)
class ApplicationSettings:
    reporting_currency: str = "USD"
    cli_session_ttl: int = 3600
    market_data: MarketDataSettings = field(default_factory=MarketDataSettings)
