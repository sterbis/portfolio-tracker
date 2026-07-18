import bcrypt

from portfolio_tracker.application.contracts.commands import (
    LogInUserCommand,
    RegisterUserCommand,
)
from portfolio_tracker.application.contracts.dtos import UserDto
from portfolio_tracker.application.persistence import UnitOfWork
from portfolio_tracker.domain.user import User

from .exceptions import InvalidUsernameOrPasswordError, UserAlreadyExistsError


class AuthService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    def register_user(self, command: RegisterUserCommand) -> UserDto:
        with self._uow as uow:
            if uow.users.get_by_username(command.username):
                raise UserAlreadyExistsError(command.username)
            
            salt = bcrypt.gensalt(rounds=12)
            password_bytes = command.password.encode("utf-8")
            password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

            user = User(username=command.username, password_hash=password_hash)
            uow.users.add(user)
            uow.commit()

            return UserDto.from_domain(user)

    def authenticate_user(self, command: LogInUserCommand) -> UserDto:
        with self._uow as uow:
            user = uow.users.get_by_username(command.username)
            if not user:
                raise InvalidUsernameOrPasswordError()

            password_bytes = command.password.encode("utf-8")
            stored_password_bytes = user.password_hash.encode("utf-8")

            if not bcrypt.checkpw(password_bytes, stored_password_bytes):
                raise InvalidUsernameOrPasswordError()

            return UserDto.from_domain(user)
