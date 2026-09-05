import sys
from datetime import date, datetime
from typing import Annotated, Any, Callable, TypeVar, overload

from filterutils import Filter, FilterError, FilterExpressionParser

import click
import typer
from rich.tree import Tree

from portfolio_tracker.application.account import (
    AccountCommandService,
    AccountQueryService,
    AssetAccountOverviewView,
    ConnectInstitutionAccountCommand,
    InstitutionAccountView,
    UpdateAssetAccountCommand,
    UpdateInstitutionAccountCommand,
)
from portfolio_tracker.application.institution import InstitutionService
from portfolio_tracker.application.shared.errors import (
    InvalidCredentialParametersError,
)
from portfolio_tracker.bootstrap_desktop import Container
from portfolio_tracker.domain.institution import InstitutionId
from portfolio_tracker.infrastructure.institution import InstitutionCode
from portfolio_tracker.infrastructure.institution.ibkr import IbkrCredentials
from portfolio_tracker.infrastructure.institution.trading_212 import (
    Trading212Credentials,
)
from portfolio_tracker.presentation.cli.console import console, error_console
from portfolio_tracker.presentation.cli.environment import CliEnvironment
from portfolio_tracker.presentation.cli.parameters import date_option, key_value_option
from portfolio_tracker.presentation.cli.parsers import (
    parse_key_value_pairs,
    parse_date,
    parse_multi_value,
    validate_non_empty,
)

from .sync import sync_accounts

T = TypeVar("T")


account_app = typer.Typer()
asset_accounts_app = typer.Typer()

account_app.add_typer(asset_accounts_app, name="asset")


@account_app.command(name="list")
def list_accounts(ctx: typer.Context) -> None:
    context: Container = ctx.obj
    service = context.get(AccountQueryService)
    institution_accounts = service.get_accounts_overview(context.active_user_id)

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
    context: Container = ctx.obj
    environment: CliEnvironment = ctx.meta["environment"]

    institution_id = resolve_input(
        parameter="--institution",
        value=institution,
        prompt=f"Institution code ({'|'.join(InstitutionCode)})",
        interactive=environment.interactive,
        value_parser=lambda value: InstitutionCode(value.upper()),
    )
    resolved_name = resolve_input(
        parameter="--name",
        value=name,
        prompt="Account name",
        interactive=environment.interactive,
        value_parser=validate_non_empty,
    )
    resolved_created_on = resolve_input(
        parameter="--created-on",
        value=created_on,
        prompt="Account created on",
        interactive=environment.interactive,
        value_parser=lambda value: parse_date(value, formats=context.DATE_FORMATS),
    )
    credential_parameters = resolve_credential_parameters(
        institution_id, credentials, context, environment.interactive
    )

    service = context.get(AccountCommandService)
    service.connect_institution_account(
        context.active_user_id,
        ConnectInstitutionAccountCommand(
            institution_id=institution_id,
            name=resolved_name,
            created_on=resolved_created_on,
            credential_parameters=credential_parameters,
        ),
    )

    console.print(f"{institution_id} '{name}' institution account successfully connected.")


@account_app.command(name="edit")
def edit_institution_account(
    ctx: typer.Context,
    account_id: Annotated[str | None, typer.Option()] = None,
    institution: Annotated[str | None, typer.Option()] = None,
    name: Annotated[str | None, typer.Option()] = None,
    created_on: Annotated[str | None, typer.Option()] = None,
    credentials: Annotated[list[str] | None, typer.Option()] = None,
    no_input: Annotated[bool, typer.Option()] = False,
) -> None:
    account_id = resolve_input(
        parameter="--account-id",
        value=institution,
        prompt=f"Institution code ({'|'.join(InstitutionCode)})",
        interactive=interactive,
        value_parser=lambda value: InstitutionCode(value.upper()),
    )
    
    context: Container = ctx.obj
    query_service = context.get(AccountQueryService)
    command_service = context.get(AccountCommandService)

    institution_account = query_service.get_institution_account(
        context.active_user_id, account_id
    )





    name, created_on, credentials_data = _prompt_institution_account_data(
        context, institution_account.institution.id, institution_account
    )
    command_service.update_institution_account(
        context.active_user_id,
        command=UpdateInstitutionAccountCommand(
            institution_account_id=institution_account.id,
            name=name,
            created_on=created_on,
            credential_parameters=credentials_data,
        ),
    )
    console.print(
        f"Institution account '{name}' ({institution_account.id}) successfully updated."
    )


@account_app.command(name="remove")
def remove_institution_account(
    ctx: typer.Context,
    account_id: Annotated[str, typer.Option(prompt=True, callback=validate_non_empty)],
    force: Annotated[bool, typer.Option()] = False,
) -> None:
    context: Container = ctx.obj
    query_service = context.get(AccountQueryService)
    command_service = context.get(AccountCommandService)
    institution_account = query_service.get_institution_account(
        context.active_user_id, account_id
    )

    if not force:
        remove = typer.confirm(
            "Are you sure you want to disconnect instititution account "
            f"'{institution_account.name}' ({institution_account.id})?",
            default=False,
        )
        if not remove:
            console.print("Operation cancelled.")
            return

    command_service.disconnect_institution_account(context.active_user_id, account_id)
    console.print(
        f"Institution account '{institution_account.name}' "
        f"({institution_account.id}) successfully disconnected."
    )


@asset_accounts_app.command(name="edit")
def edit_asset_account(
    ctx: typer.Context,
    account_id: Annotated[str, typer.Option(prompt=True, callback=validate_non_empty)],
) -> None:
    context: Container = ctx.obj
    query_service = context.get(AccountQueryService)
    command_service = context.get(AccountCommandService)
    asset_account = query_service.get_asset_account_overview(
        context.active_user_id, account_id
    )
    name, external_id = _prompt_asset_account_data(asset_account)
    command_service.update_asset_account(
        context.active_user_id,
        command=UpdateAssetAccountCommand(
            asset_account_id=account_id,
            name=name,
            external_id=external_id,
        ),
    )
    console.print(f"Asset account '{name}' ({account_id}) successfully updated.")


@asset_accounts_app.command(name="activate")
def activate_asset_account(
    ctx: typer.Context,
    account_id: Annotated[str, typer.Option(prompt=True, callback=validate_non_empty)],
    force: Annotated[bool, typer.Option()] = False,
) -> None:
    context: Container = ctx.obj
    query_service = context.get(AccountQueryService)
    command_service = context.get(AccountCommandService)
    asset_account = query_service.get_asset_account_overview(
        context.active_user_id, account_id
    )

    if not force:
        activate = typer.confirm(
            "Are you sure you want to activate asset account "
            f"'{asset_account.name}' ({asset_account.id})? ",
            default=False,
        )
        if not activate:
            console.print("Operation cancelled.")
            return

    command_service.activate_asset_account(context.active_user_id, account_id)

    sync = typer.confirm(
        "Do you want to start activated asset account sync? This might take up to few minutes.",
        default=False,
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
    account_id: Annotated[str, typer.Option(prompt=True, callback=validate_non_empty)],
    force: Annotated[bool, typer.Option()] = False,
) -> None:
    context: Container = ctx.obj
    query_service = context.get(AccountQueryService)
    command_service = context.get(AccountCommandService)
    asset_account = query_service.get_asset_account_overview(
        context.active_user_id, account_id
    )

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

    command_service.deactivate_asset_account(context.active_user_id, account_id)


@overload
def resolve_input(
    parameter: str,
    value: str | None,
    prompt: str,
    interactive: bool,
    *,
    default_value: str | None = None,
    value_parser: None = None,
) -> str: ...


@overload
def resolve_input(
    parameter: str,
    value: str | None,
    prompt: str,
    interactive: bool,
    *,
    default_value: str | None = None,
    value_parser: Callable[[str], T],
) -> T: ...


def resolve_input(
    parameter: str,
    value: str | None,
    prompt: str,
    interactive: bool,
    *,
    default_value: str | None = None,
    value_parser: Callable[[str], T] | None = None,
) -> T | str:
    if value is None:
        if not interactive:
            raise typer.BadParameter(
                f"Missing value for required {parameter} parameter."
            )

        value = typer.prompt(prompt, default=default_value)

    if value_parser is None:
        return value

    try:
        return value_parser(value)

    except ValueError as error:
        raise typer.BadParameter(f"Invalid value for {parameter}: {error}") from error


def resolve_multi_value_input(
    parameter: str,
    value: list[str] | None,
    prompt: str,
    interactive: bool,
    *,
    default_value: str | None = None,
    value_parser: Callable[[str], T] | None = None,
    separator: str = ",",
) -> list[T] | list[str]:
    if value is None:
        if not interactive:
            raise typer.BadParameter(
                f"Missing value for required {parameter} parameter."
            )

        value = typer.prompt(
            prompt,
            default=default_value,
            value_proc=lambda value: parse_multi_value(value, separator=separator),
        )

    if value_parser is None:
        return value

    try:
        return [value_parser(item) for item in value]

    except ValueError as error:
        raise typer.BadParameter(f"Invalid value for {parameter}: {error}") from error


def resolve_filter(
    model: type, field: str, expression: str | None, value_parser: Callable[[str], Any]
) -> Filter | None:
    if expression is None:
        return None
    try:
        return FilterExpressionParser.parse(
            field=field,
            expression=expression,
            item_type=model,
            value_parser=value_parser,
        )
    except FilterError as error:
        raise typer.BadParameter(str(error)) from error


def resolve_credential_parameters(
    institution_id: InstitutionCode,
    credentials: list[str] | None,
    context: Container,
    interactive: bool,
) -> dict[str, Any]:
    service = context.get(InstitutionService)
    parameters = parse_key_value_pairs(credentials) if credentials else {}

    try:
        return service.parse_credential_parameters(
            institution_id=institution_id, parameters=parameters
        )

    except InvalidCredentialParametersError as error:
        if error.metadata["unknown_parameters"]:
            raise typer.BadParameter(str(error)) from error

        if not error.metadata["missing_parameters"]:
            raise typer.BadParameter(str(error)) from error

        if not interactive:
            raise typer.BadParameter(str(error)) from error

        credentials_cls = service.get_credentials_cls(institution_id)
        secret_parameters = credentials_cls.secret_parameter_names()

        for missing_parameter in error.metadata["missing_parameters"]:
            prompt = str(missing_parameter).replace("_", " ").title()
            hide_input = missing_parameter in secret_parameters
            parameters[missing_parameter] = typer.prompt(
                prompt, confirmation_prompt=True, hide_input=hide_input
            )

    try:
        return service.parse_credential_parameters(
            institution_id=institution_id, parameters=parameters
        )

    except InvalidCredentialParametersError as error:
        raise typer.BadParameter(str(error)) from error


def _prompt_institution_account_data(
    context: Container,
    institution_id: InstitutionId,
    current_institution_account: InstitutionAccountView | None = None,
) -> tuple[str, date, dict[str, Any]]:
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
    current_credentials = (
        current_institution_account.credentials if current_institution_account else None
    )

    match institution_id:
        case InstitutionCode.INTERACTIVE_BROKERS:
            current_token = current_query_ids = None

            if isinstance(current_credentials, IbkrCredentials):
                current_token = current_credentials.flex_web_service_token
                current_query_ids = current_credentials.flex_query_ids

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
            credentials_data = {
                "flex_web_service_token": token,
                "flex_query_ids": query_ids,
            }

        case InstitutionCode.TRADING_212:
            current_api_key = current_api_secret = None
            if isinstance(current_credentials, Trading212Credentials):
                current_api_key = current_credentials.api_key
                current_api_secret = current_credentials.api_secret

            api_key = typer.prompt("API key", default=current_api_key)
            api_secret = typer.prompt("API secret", default=current_api_secret)
            credentials_data = {
                "api_key": api_key,
                "api_secret": api_secret,
            }

        case _:
            raise ValueError(f"Unexpected institution id: {institution_id}")

    return name, created_on.date(), credentials_data


def _prompt_asset_account_data(
    current_asset_account: AssetAccountOverviewView | None = None,
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
