import logging
import sys
from typing import Annotated

import typer

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
from .context import ENVIRONMENT_KEY, CliEnvironment
from .guarded_typer import GuardedTyper

logger = logging.getLogger(__name__)

SESSION_STORE_SERVICE_NAME = "portfolio-tracker"
SESSION_STORE_ENTRY_NAME = "cli-login-session"

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
    ctx: typer.Context, interactive: Annotated[bool, typer.Option()] = True
) -> None:
    ctx.meta[ENVIRONMENT_KEY] = CliEnvironment(
        is_interactive=(interactive and sys.stdin.isatty()),
    )


if __name__ == "__main__":
    app()
