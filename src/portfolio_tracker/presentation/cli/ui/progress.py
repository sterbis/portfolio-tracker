from typing import Any, AsyncGenerator, Callable

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn

from portfolio_tracker.application.sync import (
    FxSyncCompleted,
    FxSyncFailed,
    FxSyncProgress,
    FxSyncStarted,
    InstitutionSyncCompleted,
    InstitutionSyncFailed,
    InstitutionSyncStarted,
    InstrumentSyncCompleted,
    InstrumentSyncFailed,
    InstrumentSyncProgress,
    InstrumentSyncStarted,
    SyncEvent,
)
from portfolio_tracker.presentation.cli.console import console, error_console


async def render_sync_progress(
    sync_function: Callable[..., AsyncGenerator[SyncEvent, None]],
    *args: Any,
    **kwargs: Any,
) -> None:
    task_ids: dict[str, TaskID] = {}
    failed = False

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        async for event in sync_function(*args, **kwargs):
            match event:
                case InstitutionSyncStarted(
                    connection_id=connection_id,
                    connection_name=connection_name,
                ):
                    task_id = progress.add_task(
                        f"Syncing '{connection_name}' ({connection_id})...", total=100
                    )
                    task_ids[connection_id] = task_id

                case InstitutionSyncCompleted(
                    connection_id=connection_id,
                    connection_name=connection_name,
                ):
                    progress.update(
                        task_ids[connection_id],
                        completed=100,
                        description=f"[green]✔ '{connection_name}' ({connection_id}) sync completed[/green]",
                    )

                case InstitutionSyncFailed(
                    connection_id=connection_id,
                    connection_name=connection_name,
                    error=error,
                ):
                    progress.update(
                        task_ids[connection_id],
                        completed=100,
                        description=f"[red]✖ '{connection_name}' ({connection_id}) sync failed. {error}[/red]",
                    )
                    failed = True

                case FxSyncStarted(total=total):
                    task_id = progress.add_task(
                        f"Syncing FX rates for {total} dates...", total=total
                    )
                    task_ids["fx"] = task_id

                case FxSyncProgress(completed=completed, total=total):
                    progress.update(task_ids["fx"], completed=completed)

                case FxSyncCompleted():
                    progress.update(
                        task_ids["fx"],
                        description="[green]✔ FX rates sync completed[/green]",
                    )

                case FxSyncFailed(error=error):
                    progress.update(
                        task_ids["fx"],
                        description=f"[red]✖ FX rates sync failed: {error}[/red]",
                    )
                    failed = True

                case InstrumentSyncStarted(total=total):
                    task_id = progress.add_task(
                        f"Syncing market data for {total} instruments...", total=total
                    )
                    task_ids["market_data"] = task_id

                case InstrumentSyncProgress(completed=completed, total=total):
                    progress.update(task_ids["market_data"], completed=completed)

                case InstrumentSyncCompleted():
                    progress.update(
                        task_ids["market_data"],
                        description="[green]✔ Market data sync completed[/green]",
                    )

                case InstrumentSyncFailed(error=error):
                    progress.update(
                        task_ids["market_data"],
                        description=f"[red]✖ Market data sync failed: {error}[/red]",
                    )
                    failed = True

    if failed:
        if len(task_ids) > 1:
            error_console.print("[bold red]Some sync operations failed.[/bold red]")

        raise typer.Exit(1)

    if len(task_ids) > 1:
        console.print("[bold green]All sync operations completed.[/bold green]")
