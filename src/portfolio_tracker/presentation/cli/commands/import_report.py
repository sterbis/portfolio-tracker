import asyncio
from typing import Annotated

import typer

from portfolio_tracker.application.sync import ImportReportCommand
from portfolio_tracker.presentation.cli.context import (
    get_container,
    get_environment,
    get_logged_in_user_id,
)
from portfolio_tracker.presentation.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.cli.input import (
    resolve_file_input,
    resolve_input,
)
from portfolio_tracker.presentation.cli.ui.progress import render_sync_progress
from portfolio_tracker.shared.async_utils import as_async_generator

import_app = GuardedTyper()


@import_app.command(name="import")
def import_report(
    ctx: typer.Context,
    institution_account_id: Annotated[str | None, typer.Option()] = None,
    path: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    resolved_institution_account_id = resolve_input(
        "--account-id", institution_account_id, environment
    )
    resolved_path = resolve_file_input(
        "--path", path, environment, prompt="Report file"
    )

    command = ImportReportCommand(
        institution_account_id=resolved_institution_account_id, path=resolved_path
    )

    asyncio.run(
        render_sync_progress(
            as_async_generator,
            container.sync_service.import_report(user_id, command),
        )
    )
