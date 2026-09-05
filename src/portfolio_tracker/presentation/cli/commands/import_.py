import asyncio
from pathlib import Path
from typing import Annotated

import typer

from portfolio_tracker.application.sync import ImportReportCommand, SyncService
from portfolio_tracker.bootstrap_desktop import Container
from portfolio_tracker.presentation.cli.ui.progress import render_sync_progress
from portfolio_tracker.shared.async_utils import as_async_generator

import_app = typer.Typer()


@import_app.command(name="import")
def import_report(
    ctx: typer.Context,
    account_id: Annotated[str, typer.Option()],
    report_path: Annotated[
        Path,
        typer.Option(exists=True, file_okay=True, readable=True, resolve_path=True),
    ],
) -> None:
    context: Container = ctx.obj
    sync_service = context.get(SyncService)
    command = ImportReportCommand(
        institution_account_id=account_id, report_path=report_path
    )
    asyncio.run(
        render_sync_progress(
            as_async_generator,
            sync_service.import_report(context.active_user_id, command),
        )
    )
