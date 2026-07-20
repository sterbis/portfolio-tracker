from datetime import datetime
from typing import Annotated

import typer

from portfolio_tracker.application.sync import SyncService
from portfolio_tracker.bootstrap import AppContext

from ..console import error_console

sync_app = typer.Typer()


def parse_list_option(values: list[str] | None) -> list[str]:
    if not values:
        return []

    items: list[str] = []
    for value in values:
        items.extend(item.strip() for item in value.split(",") if item.strip())

    return items


@sync_app.command(name="sync")
def sync(
    ctx: typer.Context,
    account_id: Annotated[list[str] | None, typer.Option()] = None,
    asset_account_id: Annotated[list[str] | None, typer.Option()] = None,
    start: Annotated[datetime | None, typer.Option()] = None,
    end: Annotated[datetime | None, typer.Option()] = None,
    restore: Annotated[bool, typer.Option()] = False,
) -> None:
    account_ids = parse_list_option(account_id)
    asset_account_ids = parse_list_option(asset_account_id)

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

    context: AppContext = ctx.obj
    sync_service = context.get(SyncService)

    sync_service.sync(
        user_id=context.active_user_id,
        institution_account_ids=set(account_ids),
        asset_account_ids=set(asset_account_ids),
        start=start,
        end=end,
        restore=restore,
    )
