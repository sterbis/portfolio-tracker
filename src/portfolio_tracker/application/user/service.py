import bcrypt

from portfolio_tracker.application.shared.errors import (
    InvalidUsernameOrPasswordError,
    UsernameAlreadyExistsError,
)
from portfolio_tracker.application.shared.service import Service
from portfolio_tracker.domain.user import User

from .commands import (
    AuthenticateUserCommand,
    RegisterUserCommand,
)


class UserService(Service):
    def register(self, command: RegisterUserCommand) -> str:
        with self._unit_of_work() as uow:
            if uow.users.get_by_username(command.username):
                raise UsernameAlreadyExistsError(command.username)

            user = User(
                username=command.username,
                password_hash=self._hash_password(command.password),
            )

            uow.users.add(user)
            uow.commit()

            return user.id

    def authenticate(self, command: AuthenticateUserCommand) -> str:
        with self._unit_of_work() as uow:
            user = uow.users.get_by_username(command.username)
            if not user:
                raise InvalidUsernameOrPasswordError()

            self._check_password(command.password, user.password_hash)
            return user.id

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def _check_password(password: str, expected_password_hash: str) -> None:
        if not bcrypt.checkpw(
            password.encode("utf-8"), expected_password_hash.encode("utf-8")
        ):
            raise InvalidUsernameOrPasswordError()
