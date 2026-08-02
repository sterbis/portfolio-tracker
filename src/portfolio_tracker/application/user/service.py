import bcrypt

from portfolio_tracker.application.shared.exceptions import (
    InvalidUsernameOrPasswordError,
    UsernameAlreadyExistsError,
)
from portfolio_tracker.application.shared.service import ApplicationService
from portfolio_tracker.domain.user import User

from .commands import (
    AuthenticateUserCommand,
    RegisterUserCommand,
)


class UserService(ApplicationService):
    def register(self, command: RegisterUserCommand) -> str:
        with self._unit_of_work() as uow:
            if uow.users.get_by_username(command.username):
                raise UsernameAlreadyExistsError(command.username)

            salt = bcrypt.gensalt(rounds=12)
            password_bytes = command.password.encode("utf-8")
            password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

            user = User(username=command.username, password_hash=password_hash)
            uow.users.add(user)
            uow.commit()

            return user.id

    def authenticate(self, command: AuthenticateUserCommand) -> str:
        with self._unit_of_work() as uow:
            user = uow.users.get_by_username(command.username)

            if not user:
                raise InvalidUsernameOrPasswordError()

            password_bytes = command.password.encode("utf-8")
            stored_password_bytes = user.password_hash.encode("utf-8")
            if not bcrypt.checkpw(password_bytes, stored_password_bytes):
                raise InvalidUsernameOrPasswordError()

            return user.id
