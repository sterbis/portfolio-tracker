import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, overload

from dotenv import load_dotenv
from platformdirs import site_data_path, user_config_path, user_data_path


load_dotenv()


APP_NAME = "PortfolioTracker"
ENV_PREFIX = "PORTFOLIO_TRACKER_"


@dataclass(frozen=True)
class DesktopConfiguration:
    encryption_key: str
    database_path: Path
    users_data_dir: Path
    users_settings_dir: Path


def load_desktop_configuration() -> DesktopConfiguration:
    return DesktopConfiguration(
        encryption_key=get_env_var(env_var("ENCRYPTION_KEY"), required=True),
        database_path=user_data_path(APP_NAME, ensure_exists=True)/ "portfolio.db",
        users_data_dir=user_data_path(APP_NAME, ensure_exists=True) / "users",
        users_settings_dir=user_config_path(APP_NAME, ensure_exists=True) / "users",
    )


def resolve_shared_data_dir() -> Path:
    try:
        return site_data_path(APP_NAME, ensure_exists=True)
    except PermissionError:
        return user_data_path(APP_NAME, ensure_exists=True)


def env_var(name: str) -> str:
    return f"{ENV_PREFIX}{name}"


@overload
def get_env_var(name: str, required: Literal[True]) -> str: ...

@overload
def get_env_var(name: str, required: Literal[False] = False) -> str | None: ...

def get_env_var(name: str, required: bool = False) -> str | None:
    value = os.environ.get(name)
    if not value and required:
        raise EnvironmentError(f"Required environment variable '{name}' is not set.")

    return value
