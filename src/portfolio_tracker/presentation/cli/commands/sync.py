import asyncio
from datetime import datetime
from typing import Annotated

import typer

from portfolio_tracker.application.sync import (
    SyncFxRatesCommand,
    SyncInstitutionAccountsCommand,
    SyncInstrumentsCommand,
    SyncService,
)
from portfolio_tracker.bootstrap import ApplicationContext
from portfolio_tracker.presentation.cli.console import error_console
from portfolio_tracker.presentation.cli.parsers import (
    parse_date_parameter,
    parse_list_parameter,
)
from portfolio_tracker.presentation.cli.ui.progress import render_sync_progress
from portfolio_tracker.shared.async_utils import as_async_generator

sync_app = typer.Typer(invoke_without_command=True)


@sync_app.callback()
def sync_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        ctx.invoke(sync_accounts)


@sync_app.command(name="accounts")
def sync_accounts(
    ctx: typer.Context,
    account_id: Annotated[list[str] | None, typer.Option()] = None,
    asset_account_id: Annotated[list[str] | None, typer.Option()] = None,
    start: Annotated[datetime | None, typer.Option()] = None,
    end: Annotated[datetime | None, typer.Option()] = None,
    restore: Annotated[bool, typer.Option()] = False,
) -> None:
    account_ids = set(parse_list_parameter(account_id))
    asset_account_ids = set(parse_list_parameter(asset_account_id))

    if account_ids and asset_account_ids:
        error_console.print(
            "Error: Options --account-id and --asset-account-id are mutually exclusive."
        )
        raise typer.Exit(code=1)

    if restore and (start or end):
        error_console.print(
            "Error: --restore option overrides both --start and --end options."
        )
        raise typer.Exit(code=1)

    context: ApplicationContext = ctx.obj
    service = context.get(SyncService)
    command = SyncInstitutionAccountsCommand(
        user_id=context.active_user_id,
        institution_account_ids=account_ids,
        asset_account_ids=asset_account_ids,
        start=start,
        end=end,
        restore=restore,
    )
    asyncio.run(
        render_sync_progress(
            service.sync_institution_accounts, context.active_user_id, command
        )
    )


@sync_app.command(name="fx")
def sync_fx_rates(
    ctx: typer.Context,
    date: Annotated[list[str] | None, typer.Option()] = None,
) -> None:
    dates = set(
        parse_list_parameter(
            date,
            converter=lambda value: parse_date_parameter(
                value, formats=ApplicationContext.DATE_FORMATS
            ),
        )
    )
    context: ApplicationContext = ctx.obj
    service = context.get(SyncService)
    command = SyncFxRatesCommand(
        dates=dates,
        all=not dates,
    )
    asyncio.run(
        render_sync_progress(as_async_generator, service.sync_fx_rates(command))
    )


@sync_app.command(name="instruments")
def sync_instruments(
    ctx: typer.Context,
    symbol: Annotated[list[str] | None, typer.Option()] = None,
    new_only: Annotated[bool, typer.Option()] = False,
    all_: Annotated[bool, typer.Option("--all")] = False,
) -> None:
    symbols = set(parse_list_parameter(symbol))
    context: ApplicationContext = ctx.obj
    service = context.get(SyncService)
    command = SyncInstrumentsCommand(
        symbols=symbols,
        new_only=new_only,
        all=all_,
    )
    asyncio.run(
        render_sync_progress(as_async_generator, service.sync_instruments(command))
    )
