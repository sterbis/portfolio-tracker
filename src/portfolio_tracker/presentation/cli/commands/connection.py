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
from portfolio_tracker.presentation.cli.ui.tables import display_table

connection_app = GuardedTyper()


@connection_app.command(name="list")
def list_institution_connections(ctx: typer.Context) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)
    settings = get_settings(ctx)

    connections = container.institution_query_service.get_institution_connections(
        user_id
    )
    if not connections:
        console.print("No connected institutions found.")
        return

    display_table(InstitutionConnectionView, connections, settings.display.cli)


@connection_app.command(name="add")
def add_institution_connection(
    ctx: typer.Context,
    institution_code: Annotated[str | None, typer.Option()] = None,
    name: Annotated[str | None, typer.Option()] = None,
    sync_from: Annotated[str | None, typer.Option()] = None,
    credential_list: Annotated[list[str] | None, typer.Option("--credential")] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    inputs: list[Input[Any, Any]] = [
        required_enum_input("--institution-code", institution_code, InstitutionCode),
        required_str_input("--name", name),
        required_date_input("--sync-from", sync_from),
    ]
    values = resolve_inputs(environment, inputs)
    resolved_institution_code = values["--institution-code"]
    resolved_name = values["--name"]

    credential_parameters = resolve_credential_parameters(
        resolved_institution_code,
        credential_list,
        container.institution_query_service,
        environment,
    )
    connection_id = container.institution_command_service.connect_institution(
        user_id,
        ConnectInstitutionCommand(
            institution_id=resolved_institution_code,
            name=resolved_name,
            sync_from=values["--sync-from"],
            credential_parameters=credential_parameters,
        ),
    )
    console.print(
        f"Institution connection '{resolved_name}' ({connection_id}) successfully added."
    )


@connection_app.command(name="edit")
def edit_institution_connection(
    ctx: typer.Context,
    connection_id: Annotated[str | None, typer.Option()] = None,
    institution_code: Annotated[str | None, typer.Option()] = None,
    name: Annotated[str | None, typer.Option()] = None,
    sync_from: Annotated[str | None, typer.Option()] = None,
    credential_list: Annotated[list[str] | None, typer.Option("--credential")] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    command_service = container.institution_command_service
    query_service = container.institution_query_service

    connection_id = resolve_input("--connection-id", connection_id, environment)
    connection = query_service.get_institution_connection(user_id, connection_id)

    inputs: list[Input[Any, Any]] = [
        optional_prompt_enum_input(
            "--institution-code",
            institution_code,
            InstitutionCode,
            default_value=connection.institution.id,
        ),
        optional_prompt_str_input(
            "--name",
            name,
            default_value=connection.name,
        ),
        optional_prompt_date_input(
            "--sync-from",
            sync_from,
            default_value=connection.sync_from,
        ),
    ]
    values = resolve_inputs(environment, inputs)
    resolved_institution_code = values["--institution-code"]

    current_credential_parameters = (
        connection.credentials.parameters if connection.credentials else None
    )
    credential_parameters = resolve_credential_parameters(
        resolved_institution_code,
        credential_list,
        container.institution_query_service,
        environment,
        current_credential_parameters,
    )

    command_service.update_institution_connection(
        user_id,
        command=UpdateInstitutionConnectionCommand(
            connection_id=connection.id,
            name=values["--name"],
            sync_from=values["--sync-from"],
            credential_parameters=credential_parameters,
        ),
    )
    connection = query_service.get_institution_connection(user_id, connection_id)
    console.print(
        f"Institution connection '{connection.name}'"
        f"({connection.id}) successfully updated."
    )


@connection_app.command(name="remove")
def remove_institution_connection(
    ctx: typer.Context,
    connection_id: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    command_service = container.institution_command_service
    query_service = container.institution_query_service

    connection_id = resolve_input("--connection-id", connection_id, environment)
    connection = query_service.get_institution_connection(user_id, connection_id)

    if environment.is_interactive:
        remove = typer.confirm(
            "Are you sure you want to remove instititution connection "
            f"'{connection.name}' ({connection.id})?",
            default=False,
        )
        if not remove:
            console.print("Operation cancelled.")
            return

    command_service.disconnect_institution(user_id, connection_id)

    console.print(
        f"Institution connection '{connection.name}' "
        f"({connection.id}) successfully removed."
    )
