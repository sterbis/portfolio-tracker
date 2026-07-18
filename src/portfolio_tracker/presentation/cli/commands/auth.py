from typing import Annotated

import typer

from portfolio_tracker.application.contracts.commands import (
    LogInUserCommand,
    RegisterUserCommand,
)
from portfolio_tracker.application.contracts.dtos import UserDto
from portfolio_tracker.application.user import AuthService, UserAlreadyLoggedOutError
from portfolio_tracker.bootstrap import AppContext

from ..console import console
from ..session import delete_login_session, set_login_session

auth_app = typer.Typer()


@auth_app.command(name="register")
def register(
    ctx: typer.Context,
    username: Annotated[str, typer.Option(prompt=True)],
    password: Annotated[
        str, typer.Option(prompt=True, confirmation_prompt=True, hide_input=True)
    ],
) -> None:
    context: AppContext = ctx.obj
    service = context.get(AuthService)
    user = service.register_user(
        RegisterUserCommand(username=username, password=password)
    )
    console.print(f"User '{username}' successfully registered.")
    _login_user(user, context.SESSION_TTL)


@auth_app.command(name="login")
def login(
    ctx: typer.Context,
    username: Annotated[str, typer.Option(prompt=True)],
    password: Annotated[str, typer.Option(prompt=True, hide_input=True)],
) -> None:
    context: AppContext = ctx.obj
    service = context.get(AuthService)
    user = service.authenticate_user(
        LogInUserCommand(username=username, password=password)
    )
    _login_user(user, context.SESSION_TTL)


@auth_app.command(name="logout")
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


def _login_user(user: UserDto, session_ttl: int) -> None:
    set_login_session(user.id, session_ttl)
    console.print(f"User '{user.username}' successfully logged in.")
