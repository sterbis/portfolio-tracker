import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, overload
from urllib.parse import urlsplit, urlunsplit
from urllib.request import url2pathname

from dotenv import load_dotenv
from platformdirs import user_config_path, user_data_path, user_log_path

from portfolio_tracker.domain.shared import Currency

load_dotenv()


APP_NAME = "PortfolioTracker"
APP_ENV_PREFIX = "PORTFOLIO_TRACKER_"
APP_BASE_CURRENCY = Currency.USD


class StorageType(StrEnum):
    SQLITE = "sqlite"


@dataclass(frozen=True, kw_only=True)
class Configuration:
    debug: bool = False
    encryption_key: str
    storage_type: StorageType
    storage_uri: str
    users_data_dir: Path
    users_settings_dir: Path
    log_dir: Path


def load_configuration() -> Configuration:
    storage_type, storage_uri = _load_storage_configuration()

    return Configuration(
        debug=_load_debug_configuration(),
        encryption_key=_get_env_var(_env_var("ENCRYPTION_KEY"), required=True),
        storage_type=storage_type,
        storage_uri=storage_uri,
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

    if debug.lower() == "true":
        return True

    return False


def _load_storage_configuration() -> tuple[StorageType, str]:
    uri = _get_env_var(_env_var("STORAGE_URI"), required=True)
    parts = urlsplit(uri)

    type_ = StorageType(parts.scheme)
    if type_ != StorageType.SQLITE:
        return type_, uri

    clean_path = parts.path.lstrip("/")
    if not clean_path:
        raise ValueError(f"Invalid STORAGE_URI '{uri}': Missing storage location.")

    if clean_path == ":memory:":
        return type_, urlunsplit(parts._replace(scheme="file", path=":memory:"))

    is_absolute_posix = parts.path.startswith("//")
    is_absolute_win = Path(clean_path).is_absolute()

    if is_absolute_posix:
        resolved_path = Path(url2pathname(parts.path[1:]))

    elif is_absolute_win:
        resolved_path = Path(url2pathname(clean_path))

    else:
        data_dir = user_data_path(APP_NAME, appauthor=False)
        resolved_path = data_dir / clean_path

    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    return type_, urlunsplit(
        parts._replace(scheme="file", path=resolved_path.as_posix())
    )


def _env_var(name: str) -> str:
    return f"{APP_ENV_PREFIX}{name}"


@overload
def _get_env_var(name: str, required: Literal[True]) -> str: ...


@overload
def _get_env_var(name: str, required: Literal[False] = False) -> str | None: ...


def _get_env_var(name: str, required: bool = False) -> str | None:
    value = os.environ.get(name, "").strip()
    if not value and required:
        raise EnvironmentError(f"Required environment variable '{name}' is not set.")

    return value
