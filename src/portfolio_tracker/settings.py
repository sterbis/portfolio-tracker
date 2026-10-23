from dataclasses import dataclass

from portfolio_tracker.application.settings import ApplicationSettings


@dataclass(frozen=True, kw_only=True)
class TableDisplaySettings:
    active_columns: list[str]
    sort_columns: list[str]


@dataclass(frozen=True, kw_only=True)
class DisplaySettings:
    date_format: str
    time_format: str
    none_value: str
    quantity_decimal_places: int
    percent_decimal_places: int
    money_decimal_places: int
    tables: dict[str, TableDisplaySettings]


@dataclass(frozen=True, kw_only=True)
class DisplaySettingsGroup:
    cli: DisplaySettings
    gui: DisplaySettings


@dataclass(frozen=True, kw_only=True)
class Settings:
    application: ApplicationSettings
    display: DisplaySettingsGroup
