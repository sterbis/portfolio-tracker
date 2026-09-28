import asyncio
from typing import Annotated

import typer

from portfolio_tracker.application.sync import (
    SyncFxRatesCommand,
    SyncInstrumentsCommand,
)
from portfolio_tracker.presentation.cli.context import get_container
from portfolio_tracker.presentation.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.cli.input import resolve_optional_multi_value_input
from portfolio_tracker.presentation.cli.parameters import multi_value_option
from portfolio_tracker.presentation.cli.parsers import date_parser
from portfolio_tracker.presentation.cli.ui.progress import render_sync_progress
from portfolio_tracker.shared.async_utils import as_async_generator

repair_app = GuardedTyper(invoke_without_command=True)


@repair_app.command(name="fx")
def repair_fx_rates(
    ctx: typer.Context,
    dates: Annotated[list[str] | None, multi_value_option("--date")] = None,
    all_: Annotated[bool, typer.Option()] = False,
) -> None:
    container = get_container(ctx)
    resolved_dates = resolve_optional_multi_value_input(
        "--date", dates, value_parser=date_parser
    )
    command = SyncFxRatesCommand(
        dates=set(resolved_dates) if resolved_dates else set(),
        all=all_,
    )
    asyncio.run(
        render_sync_progress(
            as_async_generator, container.sync_service.sync_fx_rates(command)
        )
    )


@repair_app.command(name="instrument")
def repair_instruments(
    ctx: typer.Context,
    symbols: Annotated[list[str] | None, multi_value_option("--symbol")] = None,
    new_only: Annotated[bool, typer.Option()] = False,
    all_: Annotated[bool, typer.Option()] = False,
) -> None:
    container = get_container(ctx)
    resolved_symbols = resolve_optional_multi_value_input(
        "--symbol", symbols, value_parser=lambda value: value.upper()
    )
    command = SyncInstrumentsCommand(
        symbols=set(resolved_symbols) if resolved_symbols else set(),
        new_only=new_only,
        all=all_,
    )
    asyncio.run(
        render_sync_progress(
            as_async_generator, container.sync_service.sync_instruments(command)
        )
    )
