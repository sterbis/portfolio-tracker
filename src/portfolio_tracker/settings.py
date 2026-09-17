from dataclasses import dataclass, field

from portfolio_tracker.application.settings import ApplicationSettings
from portfolio_tracker.presentation.cli.settings import CliDisplaySettings


@dataclass(frozen=True)
class DisplaySettings:
    cli: CliDisplaySettings = field(default_factory=CliDisplaySettings)


@dataclass(frozen=True)
class Settings:
    application: ApplicationSettings = field(default_factory=ApplicationSettings)
    display: DisplaySettings = field(default_factory=DisplaySettings)
