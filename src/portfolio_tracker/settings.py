from dataclasses import dataclass

from portfolio_tracker.application.shared.settings import ApplicationSettings
from portfolio_tracker.presentation.shared.settings import DisplaySettings


@dataclass(frozen=True, kw_only=True)
class DisplaySettingsGroup:
    cli: DisplaySettings
    gui: DisplaySettings


@dataclass(frozen=True, kw_only=True)
class Settings:
    application: ApplicationSettings
    display: DisplaySettingsGroup
