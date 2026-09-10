import functools
from typing import Any, Callable, TypeVar

import typer
from typer._click.core import Context
from typer.core import TyperCommand

from portfolio_tracker.bootstrap import desktop_bootstrap

from .console import error_console
from .context import LOGIN_SESSION_KEY, SETTINGS_CACHE_KEY, get_loggin_session_store
from .login import LoginSession, LoginSessionStore

TFunction = TypeVar("TFunction", bound=Callable[..., Any])


class GuardedCommand(TyperCommand):
    def __init__(self, *args: Any, login_required: bool = True, **kwargs: Any) -> None:
        self.login_required = login_required
        super().__init__(*args, **kwargs)

    def invoke(self, ctx: Context) -> Any:
        session_store: LoginSessionStore | None = None
        session: LoginSession | None = None

        if self.login_required:
            session_store = get_loggin_session_store(ctx)
            session = session_store.load()

            if session.user_id is None:
                error_console.print("Error: Login required. Run `login` or `register`.")
                raise typer.Exit(code=1)

            if session.is_expired:
                session_store.clear()
                error_console.print("Error: Session expired. Please log in again.")
                raise typer.Exit(code=1)

        container, settings_cache = desktop_bootstrap()
        ctx.obj = container
        ctx.meta[SETTINGS_CACHE_KEY] = settings_cache

        if session_store is not None and session is not None:
            settings = settings_cache.get_settings(session.user_id)
            session = session_store.extend(
                session, settings.application.cli_login_session_ttl
            )
            ctx.meta[LOGIN_SESSION_KEY] = session

        return super().invoke(ctx)


class GuardedTyper(typer.Typer):
    def command(
        self, name: str | None = None, *, login_required: bool = True, **kwargs: Any
    ) -> Callable[[TFunction], TFunction]:
        kwargs["cls"] = functools.partial(GuardedCommand, login_required=login_required)
        return super().command(name, **kwargs)
