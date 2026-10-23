from dataclasses import dataclass

from portfolio_tracker.application.container import Container
from portfolio_tracker.shared.settings_utils import SettingsCache
from portfolio_tracker.settings import Settings

from .market_data_feed import MarketDataFeed
from .session_keeper import LoginSessionKeeper
from .tasks import TaskRunner


@dataclass(frozen=True, kw_only=True)
class GuiContext:
    user_id: str
    container: Container
    settings_cache: SettingsCache[Settings]
    session_keeper: LoginSessionKeeper
    task_runner: TaskRunner
    market_data_feed: MarketDataFeed
