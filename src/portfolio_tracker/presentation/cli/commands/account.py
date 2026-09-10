from typing import Annotated, Any

import typer
from rich.tree import Tree

from portfolio_tracker.application.account import (
    ConnectInstitutionAccountCommand,
    UpdateAssetAccountCommand,
    UpdateInstitutionAccountCommand,
)
from portfolio_tracker.infrastructure.institution import InstitutionCode
from portfolio_tracker.presentation.cli.console import console, error_console
from portfolio_tracker.presentation.cli.context import (
    get_container,
    get_environment,
    get_logged_in_user_id,
)
from portfolio_tracker.presentation.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.cli.input import (
    Input,
    optional_prompt_date_input,
    optional_prompt_enum_input,
    optional_prompt_str_input,
    required_date_input,
    required_enum_input,
    required_str_input,
    resolve_bool_input,
    resolve_credential_parameters,
    resolve_input,
    resolve_inputs,
)

from .sync import sync_accounts

account_app = GuardedTyper()
asset_accounts_app = GuardedTyper()

account_app.add_typer(asset_accounts_app, name="asset")


@account_app.command(name="list")
def list_accounts(ctx: typer.Context) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    institution_accounts = container.account_query_service.get_accounts_overview(
        user_id
    )

    if not institution_accounts:
        error_console.print(
            "No institution accounts found. "
            "To connect institution account run: 'portfolio account add'"
        )
        return

    tree = Tree("Accounts")

    for institution_account in institution_accounts:
        label = (
            f"{institution_account.institution.name} — "
            f"{institution_account.name} ({institution_account.id})"
        )
        institution_account_branch = tree.add(label)

        for asset_account in institution_account.asset_accounts:
            label = (
                f"{asset_account.name} [External ID: {asset_account.external_id}] "
                f"({asset_account.id})"
            )
            institution_account_branch.add(label)

    console.print(tree)


@account_app.command(name="add")
def add_institution_account(
    ctx: typer.Context,
    institution: Annotated[str | None, typer.Option()] = None,
    name: Annotated[str | None, typer.Option()] = None,
    created_on: Annotated[str | None, typer.Option()] = None,
    credentials: Annotated[list[str] | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    inputs: list[Input[Any, Any]] = [
        required_enum_input("--institution", institution, InstitutionCode),
        required_str_input("--name", name),
        required_date_input("--created-on", created_on),
    ]
    values = resolve_inputs(environment, inputs)
    institution_id = values["--institution"]

    credential_parameters = resolve_credential_parameters(
        institution_id, credentials, container.institution_service, environment
    )

    container.account_command_service.connect_institution_account(
        user_id,
        ConnectInstitutionAccountCommand(
            institution_id=institution_id,
            name=values["--name"],
            created_on=values["--created-on"],
            credential_parameters=credential_parameters,
        ),
    )

    console.print(
        f"{institution_id} '{name}' institution account successfully connected."
    )


@account_app.command(name="edit")
def edit_institution_account(
    ctx: typer.Context,
    account_id: Annotated[str | None, typer.Option()] = None,
    institution: Annotated[str | None, typer.Option()] = None,
    name: Annotated[str | None, typer.Option()] = None,
    created_on: Annotated[str | None, typer.Option()] = None,
    credential_list: Annotated[list[str] | None, typer.Option("--credential")] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    account_id = resolve_input("--account-id", account_id, environment)
    institution_account = container.account_query_service.get_institution_account(
        user_id, account_id
    )
    assert (
        institution_account.credentials is not None
    ), "Credentials cannot be None here."

    inputs: list[Input[Any, Any]] = [
        optional_prompt_enum_input(
            "--institution",
            institution,
            InstitutionCode,
            default_value=institution_account.institution.id,
        ),
        optional_prompt_str_input(
            "--name", name, default_value=institution_account.name
        ),
        optional_prompt_date_input(
            "--created-on", created_on, default_value=institution_account.created_on
        ),
    ]
    values = resolve_inputs(environment, inputs)

    institution_id = values["--institution"]
    credential_parameters = resolve_credential_parameters(
        institution_id,
        credential_list,
        container.institution_service,
        environment,
        institution_account.credentials.parameters,
    )

    container.account_command_service.update_institution_account(
        user_id,
        command=UpdateInstitutionAccountCommand(
            institution_account_id=institution_account.id,
            name=values["--name"],
            created_on=values["--created-on"],
            credential_parameters=credential_parameters,
        ),
    )
    console.print(
        f"Institution account '{name}' ({institution_account.id}) successfully updated."
    )


@account_app.command(name="remove")
def remove_institution_account(
    ctx: typer.Context,
    account_id: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    account_id = resolve_input("--account-id", account_id, environment)
    institution_account = container.account_query_service.get_institution_account(
        user_id, account_id
    )

    if environment.is_interactive:
        remove = typer.confirm(
            "Are you sure you want to disconnect instititution account "
            f"'{institution_account.name}' ({institution_account.id})?",
            default=False,
        )
        if not remove:
            console.print("Operation cancelled.")
            return

    container.account_command_service.disconnect_institution_account(
        user_id, account_id
    )

    console.print(
        f"Institution account '{institution_account.name}' "
        f"({institution_account.id}) successfully disconnected."
    )


@asset_accounts_app.command(name="edit")
def edit_asset_account(
    ctx: typer.Context,
    account_id: Annotated[str | None, typer.Option()] = None,
    name: Annotated[str | None, typer.Option()] = None,
    external_id: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    account_id = resolve_input("--account-id", account_id, environment)
    asset_account = container.account_query_service.get_asset_account_overview(
        user_id, account_id
    )
    inputs: list[Input[Any, Any]] = [
        optional_prompt_str_input("--name", name, default_value=asset_account.name),
        optional_prompt_str_input(
            "--external_id", external_id, default_value=asset_account.external_id
        ),
    ]
    values = resolve_inputs(environment, inputs)

    container.account_command_service.update_asset_account(
        user_id,
        command=UpdateAssetAccountCommand(
            asset_account_id=account_id,
            name=values["--name"],
            external_id=values["--external-id"],
        ),
    )
    console.print(f"Asset account '{name}' ({account_id}) successfully updated.")


@asset_accounts_app.command(name="activate")
def activate_asset_account(
    ctx: typer.Context,
    account_id: Annotated[str | None, typer.Option()] = None,
    sync: Annotated[bool | None, typer.Option("--sync/--no-sync")] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    account_id = resolve_input("--account-id", account_id, environment)
    asset_account = container.account_query_service.get_asset_account_overview(
        user_id, account_id
    )

    if environment.is_interactive:
        activate = typer.confirm(
            "Are you sure you want to activate asset account "
            f"'{asset_account.name}' ({asset_account.id})? ",
            default=False,
        )
        if not activate:
            console.print("Operation cancelled.")
            return

    container.account_command_service.activate_asset_account(user_id, account_id)

    console.print(f"Asset account '{asset_account.name}' successfully activated.")

    sync = resolve_bool_input(
        parameter="--sync",
        value=sync,
        environment=environment,
        prompt=f"Do you want to start asset account '{asset_account.name}' sync? This might take up to few minutes.",
    )

    if sync:
        ctx.invoke(
            sync_accounts,
            asset_account_id=[asset_account.id],
            restore=True,
        )


@asset_accounts_app.command(name="deactivate")
def deactivate_asset_account(
    ctx: typer.Context,
    account_id: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    account_id = resolve_input("--account-id", account_id, environment)
    asset_account = container.account_query_service.get_asset_account_overview(
        user_id, account_id
    )

    if environment.is_interactive:
        deactivate = typer.confirm(
            "Are you sure you want to deactivate asset account "
            f"'{asset_account.name}' ({asset_account.id})? "
            "All account transactions will be deleted and "
            "account will no longer contribute to portfolio.",
            default=False,
        )
        if not deactivate:
            console.print("Operation cancelled.")
            return

    container.account_command_service.deactivate_asset_account(user_id, account_id)

    console.print(f"Asset account '{asset_account.name}' successfully deactivated.")
