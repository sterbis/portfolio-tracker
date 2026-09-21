from typing import Annotated, Any

import typer

from portfolio_tracker.application.institution import (
    ConnectInstitutionCommand,
    UpdateInstitutionConnectionCommand,
)
from portfolio_tracker.application.views import InstitutionConnectionView
from portfolio_tracker.infrastructure.institution import InstitutionCode
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
    optional_prompt_date_input,
    optional_prompt_enum_input,
    optional_prompt_str_input,
    required_date_input,
    required_enum_input,
    required_str_input,
    resolve_credential_parameters,
    resolve_input,
    resolve_inputs,
)
from portfolio_tracker.presentation.cli.ui.tables import get_view_table

institution_app = GuardedTyper()


@institution_app.command(name="list")
def list_institution_connections(ctx: typer.Context) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)
    settings = get_settings(ctx)

    institution_connections = (
        container.institution_query_service.get_institution_connections(user_id)
    )
    if not institution_connections:
        console.print("No connected institutions found.")
        return

    table = get_view_table(InstitutionConnectionView)
    rendered_table = table.render(institution_connections, settings.display.cli)
    console.print(rendered_table)


@institution_app.command(name="add")
def add_institution_connection(
    ctx: typer.Context,
    institution: Annotated[str | None, typer.Option()] = None,
    name: Annotated[str | None, typer.Option()] = None,
    account_opened_on: Annotated[str | None, typer.Option()] = None,
    credential_list: Annotated[list[str] | None, typer.Option("--credential")] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    inputs: list[Input[Any, Any]] = [
        required_enum_input("--institution", institution, InstitutionCode),
        required_str_input("--name", name),
        required_date_input("--account-opened-on", account_opened_on),
    ]
    values = resolve_inputs(environment, inputs)
    institution_id = values["--institution"]

    credential_parameters = resolve_credential_parameters(
        institution_id,
        credential_list,
        container.institution_query_service,
        environment,
    )
    connection_id = container.institution_command_service.connect_institution(
        user_id,
        ConnectInstitutionCommand(
            institution_id=institution_id,
            name=values["--name"],
            account_opened_on=values["--account-opened-on"],
            credential_parameters=credential_parameters,
        ),
    )
    console.print(
        f"Institution account '{name}' ({connection_id})  successfully connected."
    )


@institution_app.command(name="edit")
def edit_institution_connection(
    ctx: typer.Context,
    connection_id: Annotated[str | None, typer.Option()] = None,
    institution: Annotated[str | None, typer.Option()] = None,
    name: Annotated[str | None, typer.Option()] = None,
    account_opened_on: Annotated[str | None, typer.Option()] = None,
    credential_list: Annotated[list[str] | None, typer.Option("--credential")] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    connection_id = resolve_input("--connection-id", connection_id, environment)
    institution_connection = (
        container.institution_query_service.get_institution_connection(
            user_id, connection_id
        )
    )

    inputs: list[Input[Any, Any]] = [
        optional_prompt_enum_input(
            "--institution",
            institution,
            InstitutionCode,
            default_value=institution_connection.institution.id,
        ),
        optional_prompt_str_input(
            "--name", name, default_value=institution_connection.name
        ),
        optional_prompt_date_input(
            "--account-opened-on",
            account_opened_on,
            default_value=institution_connection.account_opened_on,
        ),
    ]
    values = resolve_inputs(environment, inputs)
    institution_id = values["--institution"]

    current_credential_parameters = (
        institution_connection.credentials.parameters
        if institution_connection.credentials
        else None
    )
    credential_parameters = resolve_credential_parameters(
        institution_id,
        credential_list,
        container.institution_query_service,
        environment,
        current_credential_parameters,
    )

    container.institution_command_service.update_institution_connection(
        user_id,
        command=UpdateInstitutionConnectionCommand(
            institution_connection_id=institution_connection.id,
            name=values["--name"],
            account_opened_on=values["--account-opened-on"],
            credential_parameters=credential_parameters,
        ),
    )
    console.print(
        f"Institution account connection '{name}' "
        f"({institution_connection.id}) successfully updated."
    )


@institution_app.command(name="remove")
def remove_institution_connection(
    ctx: typer.Context,
    connection_id: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    connection_id = resolve_input("--connection-id", connection_id, environment)
    institution_connection = (
        container.institution_query_service.get_institution_connection(
            user_id, connection_id
        )
    )

    if environment.is_interactive:
        remove = typer.confirm(
            "Are you sure you want to disconnect instititution account "
            f"'{institution_connection.name}' ({institution_connection.id})?",
            default=False,
        )
        if not remove:
            console.print("Operation cancelled.")
            return

    container.institution_command_service.disconnect_institution(user_id, connection_id)

    console.print(
        f"Institution account '{institution_connection.name}' "
        f"({institution_connection.id}) successfully disconnected."
    )
