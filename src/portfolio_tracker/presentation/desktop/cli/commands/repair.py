import asyncio
from typing import Annotated

import typer

from portfolio_tracker.application.sync import (
    SyncFxRatesCommand,
    SyncInstrumentsCommand,
)
from portfolio_tracker.presentation.desktop.cli.context import CliContext
from portfolio_tracker.presentation.desktop.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.desktop.cli.input import resolve_optional_multi_value_input
from portfolio_tracker.presentation.desktop.cli.parameters import multi_value_option
from portfolio_tracker.presentation.desktop.cli.parsers import date_parser
from portfolio_tracker.presentation.desktop.cli.progress import display_progress
from portfolio_tracker.shared.async_utils import to_async_generator

repair_app = GuardedTyper(invoke_without_command=True)


@repair_app.command(name="fx")
def repair_fx_rates(
    ctx: typer.Context,
    dates: Annotated[list[str] | None, multi_value_option("--date")] = None,
    all_: Annotated[bool, typer.Option()] = False,
) -> None:
    context: CliContext = ctx.obj
    user_id = context.user_id
    service = context.container.sync_service

    resolved_dates = resolve_optional_multi_value_input(
        "--date", dates, value_parser=date_parser
    )
    asyncio.run(
        display_progress(
            to_async_generator(
                service.sync_fx_rates(
                    user_id,
                    command= SyncFxRatesCommand(
                        dates=set(resolved_dates) if resolved_dates else set(),
                        all=all_,
                    ),
                )
            )
        )
    )


@repair_app.command(name="instrument")
def repair_instruments(
    ctx: typer.Context,
    symbols: Annotated[list[str] | None, multi_value_option("--symbol")] = None,
    new_only: Annotated[bool, typer.Option()] = False,
    all_: Annotated[bool, typer.Option()] = False,
) -> None:
    context: CliContext = ctx.obj
    user_id = context.user_id
    service = context.container.sync_service

    resolved_symbols = resolve_optional_multi_value_input(
        "--symbol", symbols, value_parser=lambda value: value.upper()
    )
    asyncio.run(
        display_progress(
            to_async_generator(
                service.sync_instruments(
                    user_id,
                    command= SyncInstrumentsCommand(
                        symbols=set(resolved_symbols) if resolved_symbols else set(),
                        new_only=new_only,
                        all=all_,
                    ),
                )
            )
        )
    )
