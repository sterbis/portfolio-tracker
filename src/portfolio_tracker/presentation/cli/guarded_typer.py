import functools
import logging
from typing import Any, Callable, TypeVar

import typer
from typer._click.core import Context
from typer._click.exceptions import ClickException
from typer.core import TyperCommand

from portfolio_tracker.application.shared.errors import PortfolioTrackerError
from portfolio_tracker.bootstrap import bootstrap_desktop

from .console import error_console
from .context import (
    LOGIN_SESSION_KEY,
    SETTINGS_CACHE_KEY,
    get_configuration,
    get_loggin_session_store,
)
from .login import LoginSession, LoginSessionStore

TFunction = TypeVar("TFunction", bound=Callable[..., Any])

logger = logging.getLogger(__name__)


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
                error_console.print(
                    "Error: Login required. Run `portfolio login` or `portfolio register`."
                )
                raise typer.Exit(code=1)

            if session.is_expired:
                session_store.clear()
                error_console.print("Error: Session expired. Please log in again.")
                raise typer.Exit(code=1)

        configuration = get_configuration(ctx)
        container, settings_cache = bootstrap_desktop(configuration)
        ctx.obj = container
        ctx.meta[SETTINGS_CACHE_KEY] = settings_cache

        if session_store is not None and session is not None:
            settings = settings_cache.get_settings(session.user_id)
            session = session_store.extend(
                session, settings.application.cli_login_session_ttl
            )
            ctx.meta[LOGIN_SESSION_KEY] = session

        try:
            return super().invoke(ctx)

        except (typer.Exit, typer.Abort, ClickException) as error:
            raise error

        except Exception as error:
            if isinstance(error, PortfolioTrackerError):
                message = error.message
                logger.error(message)

            else:
                message = (
                    "Unexpected critical error occurred. "
                    "Please check application log for more details."
                )
                logger.critical(message, exc_info=error)

            error_console.print(f"Error: {message}")
            raise typer.Exit(code=1)


class GuardedTyper(typer.Typer):
    def command(
        self, name: str | None = None, *, login_required: bool = True, **kwargs: Any
    ) -> Callable[[TFunction], TFunction]:
        kwargs["cls"] = functools.partial(GuardedCommand, login_required=login_required)
        return super().command(name, **kwargs)
