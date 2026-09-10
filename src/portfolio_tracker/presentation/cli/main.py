import logging
import sys
from types import TracebackType
from typing import Annotated

import typer

from portfolio_tracker.application.shared.errors import PortfolioTrackerError

from .commands import (
    account_app,
    import_app,
    portfolio_app,
    sync_app,
    transaction_app,
    user_app,
)
from .console import error_console
from .context import ENVIRONMENT_KEY, LOGIN_SESSION_STORE_KEY
from .environment import CliEnvironment
from .guarded_typer import GuardedTyper
from .login import LoginSessionStore

logger = logging.getLogger(__name__)


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

app = GuardedTyper()
app.add_typer(account_app, name="account")
app.add_typer(transaction_app, name="transaction")
app.add_typer(sync_app, name="sync")

app.add_typer(user_app)
app.add_typer(import_app)
app.add_typer(portfolio_app)


@app.callback()
def main(ctx: typer.Context, no_input: Annotated[bool, typer.Option()] = False) -> None:
    ctx.meta[ENVIRONMENT_KEY] = CliEnvironment(
        is_interactive=(not no_input and sys.stdin.isatty()),
    )
    ctx.meta[LOGIN_SESSION_STORE_KEY] = LoginSessionStore()


if __name__ == "__main__":
    app()
