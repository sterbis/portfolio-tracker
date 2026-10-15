import asyncio
from typing import Annotated

import typer

from portfolio_tracker.application.sync import SyncCommand
from portfolio_tracker.presentation.cli.console import error_console
from portfolio_tracker.presentation.cli.context import (
    get_container,
    get_logged_in_user_id,
)
from portfolio_tracker.presentation.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.cli.input import resolve_optional_input
from portfolio_tracker.presentation.cli.parameters import multi_value_option
from portfolio_tracker.presentation.cli.parsers import datetime_parser
from portfolio_tracker.presentation.cli.ui.progress import display_sync_progress

sync_app = GuardedTyper()


@sync_app.command(name="sync")
def sync_portfolio(
    ctx: typer.Context,
    connection_ids: Annotated[
        list[str] | None, multi_value_option("--connection-id")
    ] = None,
    account_ids: Annotated[list[str] | None, multi_value_option("--account-id")] = None,
    start: Annotated[str | None, typer.Option()] = None,
    end: Annotated[str | None, typer.Option()] = None,
    restore: Annotated[bool, typer.Option()] = False,
) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    resolved_start = resolve_optional_input(
        parameter="--start",
        value=start,
        value_parser=datetime_parser,
    )
    resolved_end = resolve_optional_input(
        parameter="--end",
        value=start,
        value_parser=datetime_parser,
    )

    if restore and (start or end):
        error_console.print(
            "Error: --restore option overrides both --start and --end options."
        )
        raise typer.Exit(code=1)

    command = SyncCommand(
        connection_ids=(set(connection_ids) if connection_ids else set()),
        account_ids=set(account_ids) if account_ids else set(),
        start=resolved_start,
        end=resolved_end,
        restore=restore,
    )
    asyncio.run(display_sync_progress(container.sync_service.sync, user_id, command))
