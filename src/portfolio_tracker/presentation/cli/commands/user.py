from typing import Annotated

import typer

from portfolio_tracker.application.shared.errors import UserAlreadyLoggedOutError
from portfolio_tracker.application.user import (
    AuthenticateUserCommand,
    RegisterUserCommand,
)
from portfolio_tracker.presentation.cli.console import console
from portfolio_tracker.presentation.cli.context import (
    get_container,
    get_environment,
    get_loggin_session_store,
    get_settings,
)
from portfolio_tracker.presentation.cli.input import (
    resolve_input,
)

user_app = typer.Typer()


@user_app.command(name="register")
def register(
    ctx: typer.Context,
    username: Annotated[str | None, typer.Option()] = None,
    password: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)

    resolved_username = resolve_input("--username", username, environment)
    resolved_password = resolve_input("--password", password, environment, secret=True)

    container.user_service.register(
        command=RegisterUserCommand(
            username=resolved_username, password=resolved_password
        )
    )
    console.print(f"User '{username}' successfully registered.")
    ctx.invoke(
        login,
        username=resolved_username,
        password=resolved_password,
    )


@user_app.command(name="login")
def login(
    ctx: typer.Context,
    username: Annotated[str | None, typer.Option()] = None,
    password: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    session_store = get_loggin_session_store(ctx)

    session_store.clear()

    resolved_username = resolve_input("--username", username, environment)
    resolved_password = resolve_input("--password", password, environment, secret=True)

    user_id = container.user_service.authenticate(
        command=AuthenticateUserCommand(
            username=resolved_username,
            password=resolved_password,
        )
    )
    settings = get_settings(ctx, user_id)
    session_store.save(user_id, settings.application.cli_login_session_ttl)

    console.print(f"User '{resolved_username}' successfully logged in.")


@user_app.command(name="logout")
def logout(ctx: typer.Context) -> None:
    environment = get_environment(ctx)
    session_store = get_loggin_session_store(ctx)

    session = session_store.load()
    if not session.is_valid:
        raise UserAlreadyLoggedOutError()

    if environment.is_interactive:
        logout_ = typer.confirm("Are you sure you want to log out?", default=False)
        if not logout_:
            console.print("Operation cancelled.")
            return

    session_store.clear()
    console.print("Successfully logged out.")
