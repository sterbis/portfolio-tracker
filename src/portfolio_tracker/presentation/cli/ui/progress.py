from typing import Any, AsyncGenerator, Callable

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn

from portfolio_tracker.application.sync import (
    AccountsSyncCompleted,
    AccountsSyncFailed,
    AccountsSyncStarted,
    FxSyncCompleted,
    FxSyncFailed,
    FxSyncProgress,
    FxSyncStarted,
    InstrumentsSyncCompleted,
    InstrumentsSyncFailed,
    InstrumentsSyncProgress,
    InstrumentsSyncStarted,
    SyncEvent,
)

from ..console import console, error_console


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
                case AccountsSyncStarted(
                    institution_connection_id=account_id,
                    institution_connection_name=account_name,
                ):
                    task_id = progress.add_task(f"Syncing {account_name}...", total=100)
                    task_ids[account_id] = task_id

                case AccountsSyncCompleted(
                    institution_connection_id=account_id,
                    institution_connection_name=account_name,
                ):
                    progress.update(
                        task_ids[account_id],
                        completed=100,
                        description=f"[green]✔ {account_name} sync completed[/green]",
                    )

                case AccountsSyncFailed(
                    institution_connection_id=account_id,
                    institution_connection_name=account_name,
                    error=error,
                ):
                    progress.update(
                        task_ids[account_id],
                        completed=100,
                        description=f"[red]✖ {account_name} sync failed: {error}[/red]",
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

                case InstrumentsSyncStarted(total=total):
                    task_id = progress.add_task(
                        f"Syncing market data for {total} instruments...", total=total
                    )
                    task_ids["market_data"] = task_id

                case InstrumentsSyncProgress(completed=completed, total=total):
                    progress.update(task_ids["market_data"], completed=completed)

                case InstrumentsSyncCompleted():
                    progress.update(
                        task_ids["market_data"],
                        description="[green]✔ Market data sync completed[/green]",
                    )

                case InstrumentsSyncFailed(error=error):
                    progress.update(
                        task_ids["market_data"],
                        description=f"[red]✖ Market data sync failed: {error}[/red]",
                    )
                    failed = True

    if failed:
        if len(task_ids) > 1:
            error_console.print("[bold red]Some sync operations failed[/bold red]")

        raise typer.Exit(1)

    if len(task_ids) > 1:
        console.print("[bold green]All sync operations completed[/bold green]")
