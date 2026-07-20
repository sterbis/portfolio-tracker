from datetime import date, datetime
from typing import Annotated

import click
import typer
from rich.tree import Tree

from portfolio_tracker.application.account import (
    AccountCommandService,
    AccountQueryService,
)
from portfolio_tracker.application.contracts.commands import (
    ConnectInstitutionAccountCommand,
    UpdateAssetAccountCommand,
    UpdateInstitutionAccountCommand,
)
from portfolio_tracker.application.contracts.dtos import (
    AssetAccountOverviewDto,
    InstitutionAccountDto,
)
from portfolio_tracker.application.sync import SyncService
from portfolio_tracker.bootstrap import AppContext
from portfolio_tracker.domain.institution import Credentials
from portfolio_tracker.infrastructure.institution import (
    IbkrCredentials,
    InstitutionCode,
)
from portfolio_tracker.infrastructure.institution.trading_212 import (
    Trading212Credentials,
)

from ..console import console

accounts_app = typer.Typer()
asset_accounts_app = typer.Typer()

accounts_app.add_typer(asset_accounts_app, name="assets")


def validate_non_empty(value: str) -> str:
    value = value.strip()
    if not value:
        raise typer.BadParameter("Value is empty.")

    return value


@accounts_app.command(name="list")
def list_accounts(ctx: typer.Context) -> None:
    context: AppContext = ctx.obj
    query_service = context.get(AccountQueryService)
    institution_accounts = query_service.get_accounts_overview(context.active_user_id)

    if not institution_accounts:
        console.print(
            "No institution accounts found. To connect institution account, run: portfolio accounts add"
        )
        return

    tree = Tree("Accounts")

    for institution_account in institution_accounts:
        label = f"{institution_account.institution.name} — {institution_account.name} ({institution_account.id})"
        institution_account_branch = tree.add(label)

        for asset_account in institution_account.asset_accounts:
            label = f"{asset_account.name} [External ID: {asset_account.external_id}] ({asset_account.id})"
            institution_account_branch.add(label)

    console.print(tree)


@accounts_app.command(name="add")
def add_institution_account(
    ctx: typer.Context,
    institution: Annotated[
        InstitutionCode,
        typer.Option(prompt=True, case_sensitive=False),
    ],
) -> None:
    context: AppContext = ctx.obj
    service = context.get(AccountCommandService)

    name, created_on, credentials = _prompt_institution_account_data(
        context, institution
    )
    service.connect_institution_account(
        context.active_user_id,
        ConnectInstitutionAccountCommand(
            institution_id=institution,
            name=name,
            created_on=created_on,
            credentials=credentials,
        ),
    )
    console.print(f"{institution} '{name}' institution account successfully connected.")


@accounts_app.command(name="edit")
def edit_institution_account(
    ctx: typer.Context,
    account_id: Annotated[str, typer.Option(prompt=True, callback=validate_non_empty)],
) -> None:
    context: AppContext = ctx.obj
    query_service = context.get(AccountQueryService)
    command_service = context.get(AccountCommandService)

    institution_account = query_service.get_institution_account(account_id)
    name, created_on, credentials = _prompt_institution_account_data(
        context, institution_account.institution.id, institution_account
    )
    command_service.update_institution_account(
        UpdateInstitutionAccountCommand(
            institution_account_id=institution_account.id,
            name=name,
            created_on=created_on,
            credentials=credentials,
        ),
    )
    console.print(
        f"Institution account '{name}' ({institution_account.id}) successfully updated."
    )


@accounts_app.command(name="remove")
def remove_institution_account(
    ctx: typer.Context,
    account_id: Annotated[str, typer.Option(prompt=True, callback=validate_non_empty)],
    force: Annotated[bool, typer.Option()] = False,
) -> None:
    context: AppContext = ctx.obj
    query_service = context.get(AccountQueryService)
    command_service = context.get(AccountCommandService)
    institution_account = query_service.get_institution_account(account_id)

    if not force:
        remove = typer.confirm(
            "Are you sure you want to disconnect instititution account "
            f"'{institution_account.name}' ({institution_account.id})?",
            default=False,
        )
        if not remove:
            console.print("Operation cancelled.")
            return

    command_service.disconnect_institution_account(account_id)
    console.print(
        f"Institution account '{institution_account.name}' "
        f"({institution_account.id}) successfully disconnected."
    )


@asset_accounts_app.command(name="edit")
def edit_asset_account(
    ctx: typer.Context,
    account_id: Annotated[str, typer.Option(prompt=True, callback=validate_non_empty)],
) -> None:
    context: AppContext = ctx.obj
    query_service = context.get(AccountQueryService)
    command_service = context.get(AccountCommandService)

    asset_account = query_service.get_asset_account_overview(account_id)
    name, external_id = _prompt_asset_account_data(asset_account)
    command_service.update_asset_account(
        command=UpdateAssetAccountCommand(
            asset_account_id=account_id,
            name=name,
            external_id=external_id,
        )
    )
    console.print(f"Asset account '{name}' ({account_id}) successfully updated.")


@asset_accounts_app.command(name="activate")
def activate_asset_account(
    ctx: typer.Context,
    account_id: Annotated[str, typer.Option(prompt=True, callback=validate_non_empty)],
    force: Annotated[bool, typer.Option()] = False,
) -> None:
    context: AppContext = ctx.obj
    query_service = context.get(AccountQueryService)
    command_service = context.get(AccountCommandService)
    sync_service = context.get(SyncService)

    asset_account = query_service.get_asset_account_overview(account_id)

    if not force:
        activate = typer.confirm(
            "Are you sure you want to activate asset account "
            f"'{asset_account.name}' ({asset_account.id})? "
            "All account historical transactions will be synced up to the last institution account sync date.",
            default=False,
        )
        if not activate:
            console.print("Operation cancelled.")
            return

    command_service.activate_asset_account(account_id)
    sync_service.sync(
        context.active_user_id,
        asset_account_ids={account_id},
        restore=True,
    )


@asset_accounts_app.command(name="deactivate")
def deactivate_asset_account(
    ctx: typer.Context,
    account_id: Annotated[str, typer.Option(prompt=True, callback=validate_non_empty)],
    force: Annotated[bool, typer.Option()] = False,
) -> None:
    context: AppContext = ctx.obj
    query_service = context.get(AccountQueryService)
    command_service = context.get(AccountCommandService)

    asset_account = query_service.get_asset_account_overview(account_id)

    if not force:
        deactivate = typer.confirm(
            "Are you sure you want to deactivate asset account "
            f"'{asset_account.name}' ({asset_account.id})? "
            "All account transactions will be deleted and account will no longer contribute to portfolio.",
            default=False,
        )
        if not deactivate:
            console.print("Operation cancelled.")
            return

    command_service.deactivate_asset_account(account_id)


def _prompt_institution_account_data(
    context: AppContext,
    institution_id: str,
    current_institution_account: InstitutionAccountDto | None = None,
) -> tuple[str, date, Credentials]:
    current_name = current_created_on = None
    if current_institution_account:
        current_name = current_institution_account.name
        current_created_on = current_institution_account.created_on

    name: str = typer.prompt(
        "Name", default=current_name, value_proc=validate_non_empty
    )
    created_on: datetime = typer.prompt(
        "Created on",
        default=current_created_on,
        type=click.DateTime(formats=context.DATE_FORMATS),
    )

    match institution_id:
        case "IBKR":
            current_token = current_query_ids = None

            if isinstance(current_institution_account, IbkrCredentials):
                current_token = current_institution_account.flex_web_service_token
                current_query_ids = current_institution_account.flex_query_ids

            token: str = typer.prompt("Flex web service token", default=current_token)
            query_ids: list[str] = typer.prompt(
                "Flex query ids (comma-separated)",
                default=current_query_ids,
                value_proc=lambda value: [
                    query_id.strip()
                    for query_id in value.split(",")
                    if query_id.strip()
                ],
            )
            credentials: Credentials = IbkrCredentials(
                flex_web_service_token=token, flex_query_ids=query_ids
            )

        case "T212":
            current_api_key = current_api_secret = None
            if isinstance(current_institution_account, Trading212Credentials):
                current_api_key = current_institution_account.api_key
                current_api_secret = current_institution_account.api_secret

            api_key = typer.prompt("API key", default=current_api_key)
            api_secret = typer.prompt("API secret", default=current_api_secret)
            credentials = Trading212Credentials(api_key, api_secret)

        case _:
            raise ValueError(f"Unexpected institution id: {institution_id}")

    return name, created_on.date(), credentials


def _prompt_asset_account_data(
    current_asset_account: AssetAccountOverviewDto | None = None,
) -> tuple[str, str]:
    current_name = current_external_id = None
    if current_asset_account:
        current_name = current_asset_account.name
        current_external_id = current_asset_account.external_id

    name: str = typer.prompt(
        "Name", default=current_name, value_proc=validate_non_empty
    )
    external_id: str = typer.prompt(
        "External ID", default=current_external_id, value_proc=validate_non_empty
    )
    return name, external_id
