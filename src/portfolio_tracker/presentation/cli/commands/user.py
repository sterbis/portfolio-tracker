from typing import Annotated

import typer

from portfolio_tracker.application.user import (
    AuthenticateUserCommand,
    UserService,
    RegisterUserCommand,
)
from portfolio_tracker.application.shared.exceptions import UserAlreadyLoggedOutError
from portfolio_tracker.bootstrap import ApplicationContext
from portfolio_tracker.presentation.cli.console import console
from portfolio_tracker.presentation.cli.session import delete_login_session, set_login_session


user_app = typer.Typer()


@user_app.command(name="register")
def register_user(
    ctx: typer.Context,
    username: Annotated[str, typer.Option(prompt=True)],
    password: Annotated[
        str, typer.Option(prompt=True, confirmation_prompt=True, hide_input=True)
    ],
) -> None:
    context: ApplicationContext = ctx.obj
    service = context.get(UserService)
    service.register(
        RegisterUserCommand(username=username, password=password)
    )
    console.print(f"User '{username}' successfully registered.")
    ctx.invoke(
        login,
        username=username,
        password=password,
    )


@user_app.command(name="login")
def login(
    ctx: typer.Context,
    username: Annotated[str, typer.Option(prompt=True)],
    password: Annotated[str, typer.Option(prompt=True, hide_input=True)],
) -> None:
    context: ApplicationContext = ctx.obj
    service = context.get(UserService)
    user_id = service.authenticate(
        AuthenticateUserCommand(username=username, password=password)
    )
    set_login_session(user_id, context.USER_SESSION_TTL)
    console.print(f"User '{username}' successfully logged in.")


@user_app.command(name="logout")
def logout(
    force: Annotated[bool, typer.Option()] = False,
) -> None:
    if not force:
        log_out = typer.confirm("Are you sure you want to log out?", default=False)
        if not log_out:
            console.print("Operation cancelled.")
            return

    deleted = delete_login_session()
    if not deleted:
        raise UserAlreadyLoggedOutError()

    console.print("Successfully logged out.")
