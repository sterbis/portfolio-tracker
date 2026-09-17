from typing import TypeVar

from typer._click.core import Context

from portfolio_tracker.application.container import Container
from portfolio_tracker.application.shared.errors import UserNotLoggedInError
from portfolio_tracker.settings import Settings
from portfolio_tracker.shared.settings_utils import SettingsCache

from .environment import CliEnvironment
from .login import LoginSession, LoginSessionStore

TContextMetadata = TypeVar("TContextMetadata")


ENVIRONMENT_KEY = f"{__name__}.environment"
LOGIN_SESSION_STORE_KEY = f"{__name__}.login_session_store"
LOGIN_SESSION_KEY = f"{__name__}.login_session"
SETTINGS_CACHE_KEY = f"{__name__}.settings_cache"


def get_container(ctx: Context) -> Container:
    if not isinstance(ctx.obj, Container):
        raise RuntimeError(
            f"Expected Container type for ctx.obj value, got {type(ctx.obj).__name__}."
        )

    return ctx.obj


def get_environment(ctx: Context) -> CliEnvironment:
    return _get_context_metadata(ctx, ENVIRONMENT_KEY, CliEnvironment)


def get_loggin_session_store(ctx: Context) -> LoginSessionStore:
    return _get_context_metadata(ctx, LOGIN_SESSION_STORE_KEY, LoginSessionStore)


def get_logged_in_user_id(ctx: Context) -> str:
    session = _get_context_metadata(ctx, LOGIN_SESSION_KEY, LoginSession)
    if session.user_id is None:
        raise UserNotLoggedInError()

    return session.user_id


def get_settings(ctx: Context, user_id: str | None = None) -> Settings:
    return get_settings_cache(ctx).get_settings(user_id)


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
