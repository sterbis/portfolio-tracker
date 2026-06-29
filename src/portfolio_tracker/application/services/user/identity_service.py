import bcrypt

from portfolio_tracker.application.contracts.commands import (
    LogInUserCommand,
    RegisterUserCommand,
)
from portfolio_tracker.application.ports.unit_of_work import UnitOfWork
from portfolio_tracker.domain.user import User


class IdentityService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    def register_user(self, command: RegisterUserCommand) -> str:
        salt = bcrypt.gensalt(rounds=12)
        password_bytes = command.password.encode("utf-8")
        password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

        with self._uow as uow:
            if uow.users.get_by_username(command.username):
                raise ValueError("Username is already taken.")

            user = User(username=command.username, password_hash=password_hash)
            uow.users.add(user)
            uow.commit()

            return user.id

    def authenticate_user(self, command: LogInUserCommand) -> str:
        with self._uow as uow:
            user = uow.users.get_by_username(command.username)
            if not user:
                raise ValueError("Invalid username or password.")

            password_bytes = command.password.encode("utf-8")
            stored_password_bytes = user.password_hash.encode("utf-8")

            if not bcrypt.checkpw(password_bytes, stored_password_bytes):
                raise ValueError("Invalid username or password.")

            return user.id
