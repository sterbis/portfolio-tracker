from typing import Annotated

import typer

from portfolio_tracker.application.user import (
    AuthenticateUserCommand,
    RegisterUserCommand,
)
from portfolio_tracker.presentation.desktop.cli.console import console
from portfolio_tracker.presentation.desktop.cli.context import CliContext
from portfolio_tracker.presentation.desktop.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.desktop.cli.input import (
    resolve_input,
)

user_app = GuardedTyper()


@user_app.command(name="register", login_required=False)
def register(
    ctx: typer.Context,
    username: Annotated[str | None, typer.Option()] = None,
    password: Annotated[str | None, typer.Option()] = None,
) -> None:
    context: CliContext = ctx.obj
    environment = context.environment
    service = context.container.user_service

    resolved_username = resolve_input("--username", username, environment)
    resolved_password = resolve_input(
        "--password", password, environment, hide_input=True, confirmation_prompt=True
    )

    user_id = service.register(
        command=RegisterUserCommand(
            username=resolved_username, password=resolved_password
        )
    )
    console.print(f"User '{resolved_username}' ({user_id}) successfully registered.")
    ctx.invoke(
        login,
        ctx=ctx,
        username=resolved_username,
        password=resolved_password,
    )


@user_app.command(name="login", login_required=False, allow_invalid_settings=True)
def login(
    ctx: typer.Context,
    username: Annotated[str | None, typer.Option()] = None,
    password: Annotated[str | None, typer.Option()] = None,
) -> None:
    context: CliContext = ctx.obj
    environment = context.environment
    service = context.container.user_service

    resolved_username = resolve_input("--username", username, environment)
    resolved_password = resolve_input(
        "--password", password, environment, hide_input=True
    )

    user_id = service.authenticate(
        command=AuthenticateUserCommand(
            username=resolved_username,
            password=resolved_password,
        )
    )
    context.log_in(user_id)
    console.print(f"User '{resolved_username}' ({user_id}) successfully logged in.")


@user_app.command(name="logout", login_required=False)
def logout(ctx: typer.Context) -> None:
    context: CliContext = ctx.obj
    environment = context.environment

    if environment.is_interactive:
        logout_ = typer.confirm("Are you sure you want to log out?", default=False)
        if not logout_:
            console.print("Operation cancelled.")
            return

    context.log_out()
    console.print("Successfully logged out.")
