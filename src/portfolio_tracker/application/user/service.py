from portfolio_tracker.application.persistence import StorageConnectionFactory
from portfolio_tracker.application.security import PasswordHasher
from portfolio_tracker.application.shared.errors import (
    InvalidUsernameOrPasswordError,
    UsernameAlreadyExistsError,
)
from portfolio_tracker.application.shared.service import CommandService
from portfolio_tracker.domain.user import User

from .commands import (
    AuthenticateUserCommand,
    RegisterUserCommand,
)


class UserService(CommandService):
    def __init__(
        self,
        storage_connection_factory: StorageConnectionFactory,
        password_hasher: PasswordHasher,
    ) -> None:
        super().__init__(storage_connection_factory)
        self._password_hasher = password_hasher

    def register(self, command: RegisterUserCommand) -> str:
        with self._unit_of_work() as uow:
            if uow.users.get_by_username(command.username):
                raise UsernameAlreadyExistsError(command.username)

            user = User(
                username=command.username,
                password_hash=self._password_hasher.hash(command.password),
            )

            uow.users.add(user)
            uow.commit()

            return user.id

    def authenticate(self, command: AuthenticateUserCommand) -> str:
        with self._unit_of_work() as uow:
            user = uow.users.get_by_username(command.username)
            if not user:
                raise InvalidUsernameOrPasswordError()

            if not self._password_hasher.verify(command.password, user.password_hash):
                raise InvalidUsernameOrPasswordError()

            return user.id
