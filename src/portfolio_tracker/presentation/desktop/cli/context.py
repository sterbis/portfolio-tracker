from typing import TypeVar

from typer._click.core import Context

from portfolio_tracker.application.container import Container
from portfolio_tracker.infrastructure.configuration import Configuration
from portfolio_tracker.presentation.desktop.session import LoginSessionStore
from portfolio_tracker.settings import Settings
from portfolio_tracker.shared.settings_utils import SettingsCache

from .environment import CliEnvironment


TContextMetadata = TypeVar("TContextMetadata")


CONFIGURATION_KEY = f"{__name__}.configuration"
ENVIRONMENT_KEY = f"{__name__}.environment"
LOGIN_SESSION_STORE_KEY = f"{__name__}.login_session_store"
LOGGED_IN_USER_ID_KEY = f"{__name__}.logged_user_id"
SETTINGS_CACHE_KEY = f"{__name__}.settings_cache"


def get_container(ctx: Context) -> Container:
    if not isinstance(ctx.obj, Container):
        raise RuntimeError(
            f"Expected Container type for ctx.obj value, got {type(ctx.obj).__name__}."
        )

    return ctx.obj


def get_environment(ctx: Context) -> CliEnvironment:
    return _get_context_metadata(ctx, ENVIRONMENT_KEY, CliEnvironment)


def get_configuration(ctx: Context) -> Configuration:
    return _get_context_metadata(ctx, CONFIGURATION_KEY, Configuration)


def get_login_session_store(ctx: Context) -> LoginSessionStore:
    return _get_context_metadata(ctx, LOGIN_SESSION_STORE_KEY, LoginSessionStore) # type: ignore[type-abstract]


def get_logged_in_user_id(ctx: Context) -> str:
    return _get_context_metadata(ctx, LOGGED_IN_USER_ID_KEY, str)


def get_settings(ctx: Context, user_id: str | None = None) -> Settings:
    return get_settings_cache(ctx).get(user_id)


def get_settings_cache(ctx: Context) -> SettingsCache[Settings]:
    return _get_context_metadata(ctx, SETTINGS_CACHE_KEY, SettingsCache)


def _get_context_metadata(
    ctx: Context, key: str, value_type: type[TContextMetadata]
) -> TContextMetadata:
    value = ctx.meta.get(key)
    if not isinstance(value, value_type):
        raise RuntimeError(
            f"Expected {value_type.__name__} type for ctx.meta '{key}' value, "
            f"got {type(value).__name__}."
        )

    return value
