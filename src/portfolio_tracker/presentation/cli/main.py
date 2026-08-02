import logging
import sys
import time
from types import TracebackType

import typer

from portfolio_tracker.application.shared.exceptions import ApplicationError
from portfolio_tracker.bootstrap import bootstrap_app, ApplicationContext

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
from .session import delete_login_session, get_login_session, set_login_session

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

    if isinstance(exc_value, ApplicationError):
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


@app.callback()
def main(ctx: typer.Context) -> None:
    auth_free_commands = ("register", "login", "logout")
    context: ApplicationContext = ctx.obj

    command = ctx.invoked_subcommand
    if not command:
        return

    active_user_id, session_expiration = get_login_session()

    if not active_user_id and command not in auth_free_commands:
        error_console.print("Error: Login required.")
        error_console.print("To log in, run: portfolio login")
        error_console.print("To register, run: portfolio register")
        raise typer.Exit(code=1)

    if session_expiration and time.time() > session_expiration:
        delete_login_session()
        error_console.print("Session expired due to inactivity. Please log in again.")
        raise typer.Exit(code=1)

    if active_user_id:
        if command in auth_free_commands:
            delete_login_session()
            active_user_id = None

        else:
            set_login_session(active_user_id, context.USER_SESSION_TTL)

    ctx.obj = bootstrap_app(active_user_id)


if __name__ == "__main__":
    app()
