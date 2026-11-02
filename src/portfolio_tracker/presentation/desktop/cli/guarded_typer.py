import functools
import logging
from typing import Any, Callable, TypeVar

import typer
from typer._click.core import Context
from typer._click.exceptions import ClickException
from typer.core import TyperCommand

from portfolio_tracker.application.shared.errors import PortfolioTrackerError
from portfolio_tracker.bootstrap import bootstrap
from portfolio_tracker.presentation.desktop.session import (
    LoginSessionStore,
    LoginSession,
)
from portfolio_tracker.shared.settings_utils import SettingsValidationError
from portfolio_tracker.infrastructure.configuration import load_configuration
from portfolio_tracker.infrastructure.logging import configure_logging
from portfolio_tracker.infrastructure.keyring_session_store import (
    KeyringLoginSessionStore,
)
from portfolio_tracker.settings import Settings
from portfolio_tracker.shared.settings_utils import SettingsCache

from .console import error_console
from .context import ENVIRONMENT_KEY, CliContext, CliEnvironment

TFunction = TypeVar("TFunction", bound=Callable[..., Any])

logger = logging.getLogger(__name__)

SESSION_STORE_SERVICE_NAME = "portfolio-tracker"
SESSION_STORE_ENTRY_NAME = "cli-login-session"


class GuardedCommand(TyperCommand):
    def __init__(
        self,
        *args: Any,
        login_required: bool = True,
        allow_invalid_settins: bool = False,
        **kwargs: Any,
    ) -> None:
        self.login_required = login_required
        self.allow_default_settings = allow_invalid_settins
        super().__init__(*args, **kwargs)

    def invoke(self, ctx: Context) -> Any:
        log_file = None

        try:
            configuration = load_configuration()
            log_file = configure_logging(configuration)
            logger.info("Running command: '%s'", ctx.command_path)

            session_store = KeyringLoginSessionStore(
                SESSION_STORE_SERVICE_NAME, SESSION_STORE_ENTRY_NAME
            )
            user_id = None
            if self.login_required:
                user_id = self._resolve_user(session_store)

            container, settings_cache = bootstrap(configuration)

            if user_id and not container.user_service.exists(user_id):
                error_console.print(
                    "Error: Login required. Run `portfolio login` or `portfolio register`."
                )
                raise typer.Exit(code=1)

            context = CliContext(
                current_user_id=user_id,
                container=container,
                settings_cache=settings_cache,
                session_store=session_store,
                environment=ctx.meta.get(ENVIRONMENT_KEY, CliEnvironment(is_interactive=False)),
            )
            self._validate_settings(context)
            ctx.obj = context

            result = super().invoke(ctx)
            context.touch_session()
            return result

        except typer.Exit as error:
            if error.exit_code == 0:
                context.touch_session()

            raise error

        except (typer.Abort, ClickException) as error:
            raise error

        except PortfolioTrackerError as error:
            logger.error(error.message)
            error_console.print(f"Error: {error.message}")
            raise typer.Exit(code=1)

        except Exception as error:
            message = (
                "Unexpected critical error occurred. "
                f"Please check application log for more details:\n{log_file}"
            )
            logger.critical(message, exc_info=error)
            error_console.print(f"Error: {message}")
            raise typer.Exit(code=1)

        except KeyboardInterrupt as error:
            error_console.print("\nPortfolio Tracker closed.")
            raise typer.Exit(code=130)

    def _resolve_user(self, session_store: LoginSessionStore) -> str:
        session = session_store.load()

        if session is None:
            error_console.print(
                "Error: Login required. Run `portfolio login` or `portfolio register`."
            )
            raise typer.Exit(code=1)

        if session.is_expired():
            session_store.clear()
            error_console.print("Error: Session expired. Please log in again.")
            raise typer.Exit(code=1)

        return session.user_id

    def _validate_settings(self, context: CliContext) -> None:
        if self.login_required and not self.allow_default_settings:
            context.settings


class GuardedTyper(typer.Typer):
    def command(
        self,
        name: str | None = None,
        *,
        login_required: bool = True,
        allow_invalid_settings: bool = False,
        **kwargs: Any,
    ) -> Callable[[TFunction], TFunction]:
        kwargs["cls"] = functools.partial(
            GuardedCommand,
            login_required=login_required,
            allow_invalid_settins=allow_invalid_settings,
        )
        return super().command(name, **kwargs)
