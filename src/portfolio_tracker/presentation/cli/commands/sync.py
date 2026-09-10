import asyncio
from typing import Annotated

import typer

from portfolio_tracker.application.sync import (
    SyncFxRatesCommand,
    SyncInstitutionAccountsCommand,
    SyncInstrumentsCommand,
)
from portfolio_tracker.presentation.cli.console import error_console
from portfolio_tracker.presentation.cli.context import (
    get_container,
    get_logged_in_user_id,
)
from portfolio_tracker.presentation.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.cli.input import (
    resolve_optional_input,
    resolve_optional_multi_value_input,
)
from portfolio_tracker.presentation.cli.parameters import multi_value_option
from portfolio_tracker.presentation.cli.parsers import (
    date_parser,
    datetime_parser,
)
from portfolio_tracker.presentation.cli.ui.progress import render_sync_progress
from portfolio_tracker.shared.async_utils import as_async_generator

sync_app = GuardedTyper(invoke_without_command=True)


@sync_app.callback()
def sync_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        ctx.invoke(sync_accounts)


@sync_app.command(name="account")
def sync_accounts(
    ctx: typer.Context,
    institution_account_id: Annotated[list[str] | None, multi_value_option()] = None,
    asset_account_id: Annotated[
        list[str] | None, multi_value_option("--asset-account-id")
    ] = None,
    start: Annotated[str | None, typer.Option()] = None,
    end: Annotated[str | None, typer.Option()] = None,
    restore: Annotated[bool, typer.Option()] = False,
) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    institution_account_ids = (
        set(institution_account_id) if institution_account_id else set()
    )
    asset_account_ids = set(asset_account_id) if asset_account_id else set()

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

    command = SyncInstitutionAccountsCommand(
        institution_account_ids=set(institution_account_ids),
        asset_account_ids=set(asset_account_ids),
        start=resolved_start,
        end=resolved_end,
        restore=restore,
    )
    asyncio.run(
        render_sync_progress(
            container.sync_service.sync_institution_accounts, user_id, command
        )
    )


@sync_app.command(name="fx")
def sync_fx_rates(
    ctx: typer.Context,
    date_: Annotated[list[str] | None, multi_value_option()] = None,
    all_: Annotated[bool, typer.Option()] = False,
) -> None:
    container = get_container(ctx)
    dates = resolve_optional_multi_value_input(
        "--date", date_, value_parser=date_parser
    )
    command = SyncFxRatesCommand(
        dates=set(dates) if dates else set(),
        all=all_,
    )
    asyncio.run(
        render_sync_progress(
            as_async_generator, container.sync_service.sync_fx_rates(command)
        )
    )


@sync_app.command(name="instrument")
def sync_instruments(
    ctx: typer.Context,
    symbol: Annotated[list[str] | None, multi_value_option()] = None,
    new_only: Annotated[bool, typer.Option()] = False,
    all_: Annotated[bool, typer.Option()] = False,
) -> None:
    container = get_container(ctx)
    symbols = resolve_optional_multi_value_input(
        "--symbol", symbol, value_parser=lambda value: value.upper()
    )
    command = SyncInstrumentsCommand(
        symbols=set(symbols) if symbols else set(),
        new_only=new_only,
        all=all_,
    )
    asyncio.run(
        render_sync_progress(
            as_async_generator, container.sync_service.sync_instruments(command)
        )
    )
