import asyncio
from typing import Annotated

import click
import typer

from portfolio_tracker.application.sync import SyncCommand
from portfolio_tracker.presentation.desktop.cli.context import CliContext
from portfolio_tracker.presentation.desktop.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.desktop.cli.input import resolve_optional_input
from portfolio_tracker.presentation.desktop.cli.parameters import multi_value_option
from portfolio_tracker.presentation.desktop.cli.parsers import datetime_parser
from portfolio_tracker.presentation.desktop.cli.progress import display_progress

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
    if restore and (start or end):
        raise click.UsageError("--restore cannot be combined with --start or --end.")
    
    context: CliContext = ctx.obj
    user_id = context.user_id
    service = context.container.sync_service

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

    asyncio.run(
        display_progress(
            service.sync(
                user_id,
                command=SyncCommand(
                    connection_ids=(set(connection_ids) if connection_ids else set()),
                    account_ids=set(account_ids) if account_ids else set(),
                    start=resolved_start,
                    end=resolved_end,
                    restore=restore,
                )
            )
        )
    )
