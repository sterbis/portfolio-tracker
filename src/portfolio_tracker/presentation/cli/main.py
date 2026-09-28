import logging
import sys
from typing import Annotated

import typer

from portfolio_tracker.infrastructure.configuration import load_desktop_configuration
from portfolio_tracker.infrastructure.logging import configure_desktop_cli_logging

from .commands import (
    account_app,
    connection_app,
    import_app,
    overview_app,
    repair_app,
    settings_app,
    sync_app,
    transaction_app,
    user_app,
)
from .context import CONFIGURATION_KEY, ENVIRONMENT_KEY, LOGIN_SESSION_STORE_KEY
from .environment import CliEnvironment
from .guarded_typer import GuardedTyper
from .login import LoginSessionStore

logger = logging.getLogger(__name__)


app = GuardedTyper()
app.add_typer(account_app, name="account")
app.add_typer(import_app)
app.add_typer(connection_app, name="connection")
app.add_typer(overview_app)
app.add_typer(repair_app, name="repair")
app.add_typer(settings_app, name="settings")
app.add_typer(sync_app)
app.add_typer(transaction_app, name="transaction")
app.add_typer(user_app)


@app.callback()
def app_callback(
    ctx: typer.Context, no_input: Annotated[bool, typer.Option()] = False
) -> None:
    configuration = load_desktop_configuration()
    configure_desktop_cli_logging(configuration)

    logger.info("Run command: '%s'", " ".join(sys.argv))

    ctx.meta[CONFIGURATION_KEY] = configuration
    ctx.meta[ENVIRONMENT_KEY] = CliEnvironment(
        is_interactive=(not no_input and sys.stdin.isatty()),
    )
    ctx.meta[LOGIN_SESSION_STORE_KEY] = LoginSessionStore()


if __name__ == "__main__":
    app()
