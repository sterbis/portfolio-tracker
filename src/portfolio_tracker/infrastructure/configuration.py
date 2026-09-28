import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, overload

from dotenv import load_dotenv
from platformdirs import user_config_path, user_data_path, user_log_path

from portfolio_tracker.domain.shared import Currency

load_dotenv()


APP_NAME = "PortfolioTracker"
APP_ENV_PREFIX = "PORTFOLIO_TRACKER_"
APP_BASE_CURRENCY = Currency.USD


@dataclass(frozen=True, kw_only=True)
class DesktopConfiguration:
    debug: bool = False
    encryption_key: str
    database_path: Path
    users_data_dir: Path
    users_settings_dir: Path
    log_dir: Path


def load_desktop_configuration() -> DesktopConfiguration:
    return DesktopConfiguration(
        debug=_load_debug_configuration(),
        encryption_key=_get_env_var(_env_var("ENCRYPTION_KEY"), required=True),
        database_path=user_data_path(APP_NAME, appauthor=False, ensure_exists=True)
        / "portfolio.db",
        users_data_dir=user_data_path(APP_NAME, appauthor=False, ensure_exists=True)
        / "Users",
        users_settings_dir=user_config_path(
            APP_NAME, appauthor=False, ensure_exists=True
        )
        / "Users",
        log_dir=user_log_path(APP_NAME, appauthor=False, ensure_exists=True),
    )


def _load_debug_configuration() -> bool:
    debug = _get_env_var(_env_var("DEBUG"))
    if debug is None:
        return False

    if debug.strip().lower() == "true":
        return True

    return False


def _env_var(name: str) -> str:
    return f"{APP_ENV_PREFIX}{name}"


@overload
def _get_env_var(name: str, required: Literal[True]) -> str: ...


@overload
def _get_env_var(name: str, required: Literal[False] = False) -> str | None: ...


def _get_env_var(name: str, required: bool = False) -> str | None:
    value = os.environ.get(name)
    if not value and required:
        raise EnvironmentError(f"Required environment variable '{name}' is not set.")

    return value
