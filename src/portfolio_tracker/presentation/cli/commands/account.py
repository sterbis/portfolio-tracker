from typing import Annotated, Any

import typer

from portfolio_tracker.application.account import UpdateAssetAccountCommand
from portfolio_tracker.application.views import AssetAccountView
from portfolio_tracker.presentation.cli.console import console
from portfolio_tracker.presentation.cli.context import (
    get_container,
    get_environment,
    get_logged_in_user_id,
    get_settings,
)
from portfolio_tracker.presentation.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.cli.input import (
    Input,
    optional_prompt_str_input,
    resolve_bool_input,
    resolve_input,
    resolve_inputs,
)
from portfolio_tracker.presentation.cli.ui.tables import get_view_table

from .sync import sync_accounts

account_app = GuardedTyper()


@account_app.command(name="list")
def list_accounts(ctx: typer.Context) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)
    settings = get_settings(ctx)

    accounts = container.account_query_service.get_accounts(user_id)

    if not accounts:
        console.print("No accounts found.")
        return

    table = get_view_table(AssetAccountView)
    rendered_table = table.render(accounts, settings.display.cli)
    console.print(rendered_table)


@account_app.command(name="edit")
def edit_account(
    ctx: typer.Context,
    account_id: Annotated[str | None, typer.Option()] = None,
    name: Annotated[str | None, typer.Option()] = None,
    external_id: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    account_id = resolve_input("--account-id", account_id, environment)
    account = container.account_query_service.get_account(user_id, account_id)
    inputs: list[Input[Any, Any]] = [
        optional_prompt_str_input("--name", name, default_value=account.name),
        optional_prompt_str_input(
            "--external_id", external_id, default_value=account.external_id
        ),
    ]
    values = resolve_inputs(environment, inputs)

    container.account_command_service.update_account(
        user_id,
        command=UpdateAssetAccountCommand(
            account_id=account_id,
            name=values["--name"],
            external_id=values["--external-id"],
        ),
    )
    console.print(f"Account '{name}' ({account_id}) successfully updated.")


@account_app.command(name="activate")
def activate_account(
    ctx: typer.Context,
    account_id: Annotated[str | None, typer.Option()] = None,
    sync: Annotated[bool | None, typer.Option("--sync/--no-sync")] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    account_id = resolve_input("--account-id", account_id, environment)
    account = container.account_query_service.get_account(user_id, account_id)

    if environment.is_interactive:
        activate = typer.confirm(
            "Are you sure you want to activate account "
            f"'{account.name}' ({account.id})? ",
            default=False,
        )
        if not activate:
            console.print("Operation cancelled.")
            return

    container.account_command_service.activate_account(user_id, account_id)
    console.print(f"Account '{account.name}' successfully activated.")

    sync = resolve_bool_input(
        parameter="--sync",
        value=sync,
        environment=environment,
        prompt=(
            f"Do you want to start account '{account.name}' sync? "
            "This might take up to few minutes."
        ),
    )

    if sync:
        ctx.invoke(
            sync_accounts,
            account_id=[account.id],
            restore=True,
        )


@account_app.command(name="deactivate")
def deactivate_account(
    ctx: typer.Context,
    account_id: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    account_id = resolve_input("--account-id", account_id, environment)
    account = container.account_query_service.get_account(user_id, account_id)

    if environment.is_interactive:
        deactivate = typer.confirm(
            "Are you sure you want to deactivate account "
            f"'{account.name}' ({account.id})? "
            "All account transactions will be deleted and "
            "account will no longer contribute to portfolio.",
            default=False,
        )
        if not deactivate:
            console.print("Operation cancelled.")
            return

    container.account_command_service.deactivate_account(user_id, account_id)
    console.print(f"Account '{account.name}' successfully deactivated.")
