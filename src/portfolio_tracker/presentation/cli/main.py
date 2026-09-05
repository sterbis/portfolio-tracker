import logging
import sys
from types import TracebackType
from typing import Annotated

import typer

from portfolio_tracker.application.shared.errors import PortfolioTrackerError
from portfolio_tracker.bootstrap_desktop import bootstrap_desktop

from .commands import (
    account_app,
    cash_balance_app,
    import_app,
    position_app,
    sync_app,
    transaction_app,
    user_app,
)
from .console import error_console
from .environment import CliEnvironment
from .session import UserSession

logger = logging.getLogger(__name__)

app = typer.Typer()
app.add_typer(account_app, name="account")
app.add_typer(transaction_app, name="transaction")
app.add_typer(sync_app, name="sync")

app.add_typer(user_app, name="")
app.add_typer(import_app, name="")
app.add_typer(cash_balance_app, name="")
app.add_typer(position_app, name="")


def global_exception_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    traceback: TracebackType | None,
) -> None:
    exc_info = (exc_type, exc_value, traceback)

    if isinstance(exc_value, PortfolioTrackerError):
        message = exc_value.message
        logger.error(message, exc_info=exc_info)

    else:
        message = (
            "Unexpected critical system error occurred. "
            "Please check application log for more details."
        )
        logger.critical(message, exc_info=exc_info)

    error_console.print(f"Error: {message}")
    sys.exit(1)


sys.excepthook = global_exception_handler


SESSION_KEY = f"{__name__}.session"
USER_SESSION_TTL = 1800  # 30m = 30 * 60s = 1800s


@app.callback()
def main(
    ctx: typer.Context,
    no_input: Annotated[bool, typer.Option()] = False,
) -> None:
    environment = CliEnvironment(
        interactive=(not no_input and sys.stdin.isatty()),
    )

    command = ctx.invoked_subcommand
    if not command:
        return

    ctx.command.name

    auth_free_commands = ("register", "login", "logout")

    session = UserSession.get()

    if not session and command not in auth_free_commands:
        error_console.print("Error: Login required.")
        error_console.print("To log in, run: portfolio login")
        error_console.print("To register, run: portfolio register")
        raise typer.Exit(code=1)

    if session and session.is_expired:
        session.clear()
        error_console.print("Session expired due to inactivity. Please log in again.")
        raise typer.Exit(code=1)

    if command in auth_free_commands:
        session.clear()

    else:
        session.refresh()

    ctx.obj = bootstrap_desktop()



def get_session(ctx: typer.Context) -> UserSession:
    value = ctx.meta[SESSION_KEY]
    assert isinstance(value, UserSession), f"Expected CliSession for ctx.meta '{SESSION_KEY}', got {type(value).__name__}."
    return value


def get_application_context(ctx: typer.Context) -> Container:
    assert isinstance(ctx.obj, Container), f"Expected ApplicationContext, got {type(ctx.obj).__name__}."
    return ctx.obj


if __name__ == "__main__":
    app()
