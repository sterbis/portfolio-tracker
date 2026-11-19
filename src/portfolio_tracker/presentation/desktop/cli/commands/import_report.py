import asyncio
from typing import Annotated

import typer

from portfolio_tracker.application.sync import ImportReportCommand
from portfolio_tracker.presentation.desktop.cli.context import CliContext
from portfolio_tracker.presentation.desktop.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.desktop.cli.input import (
    resolve_file_input,
    resolve_input,
)
from portfolio_tracker.presentation.desktop.cli.progress import display_progress
from portfolio_tracker.shared.async_utils import to_async_generator

import_app = GuardedTyper()


@import_app.command(name="import")
def import_report(
    ctx: typer.Context,
    connection_id: Annotated[str | None, typer.Option()] = None,
    path: Annotated[str | None, typer.Option()] = None,
) -> None:
    context: CliContext = ctx.obj
    environment = context.environment
    user_id = context.user_id
    service = context.container.sync_service

    resolved_connection_id = resolve_input(
        "--connection-id", connection_id, environment
    )
    resolved_path = resolve_file_input(
        "--path", path, environment, prompt="Report file"
    )

    command = ImportReportCommand(
        connection_id=resolved_connection_id, path=resolved_path
    )

    asyncio.run(
        display_progress(
            to_async_generator(service.import_report(user_id, command))
        )
    )
