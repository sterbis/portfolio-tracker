import logging
import sys
import time
from types import TracebackType

import typer

from portfolio_tracker.application.contracts.exceptions import AppError
from portfolio_tracker.application.sync import SyncError
from portfolio_tracker.bootstrap import bootstrap_app

from .commands import (
    accounts_app,
    auth_app,
    cash_balance_app,
    positions_app,
    sync_app,
    transactions_app,
)
from .console import error_console
from .session import delete_login_session, get_login_session, set_login_session

logger = logging.getLogger(__name__)


def global_exception_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    traceback: TracebackType | None,
) -> None:
    exc_info = (exc_type, exc_value, traceback)

    if isinstance(exc_value, AppError):
        message = exc_value.message

        if isinstance(exc_value, SyncError):
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


app = typer.Typer()
app.add_typer(accounts_app, name="accounts")
app.add_typer(transactions_app, name="transactions")

app.add_typer(auth_app, name="")
app.add_typer(cash_balance_app, name="")
app.add_typer(positions_app, name="")
app.add_typer(sync_app, name="")


@app.callback()
def main(ctx: typer.Context) -> None:
    auth_commands = ("register", "login", "logout")
    session_ttl = 1800

    command = ctx.invoked_subcommand
    if not command:
        return

    active_user_id, session_expiration = get_login_session()

    if not active_user_id and command not in auth_commands:
        error_console.print("Error: Login required.")
        error_console.print("To log in, run: portfolio login")
        error_console.print("To register, run: portfolio register")
        raise typer.Exit(code=1)

    if session_expiration and time.time() > session_expiration:
        delete_login_session()
        error_console.print("Session expired due to inactivity. Please log in again.")
        raise typer.Exit(code=1)

    if active_user_id:
        if command in auth_commands:
            delete_login_session()
            active_user_id = None

        else:
            set_login_session(active_user_id, session_ttl)

    ctx.obj = bootstrap_app(active_user_id)


if __name__ == "__main__":
    app()
