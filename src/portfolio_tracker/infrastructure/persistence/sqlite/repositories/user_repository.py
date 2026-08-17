from filterutils import FilterNode, Operator

from portfolio_tracker.application.persistence import UserRepository
from portfolio_tracker.domain.user import User
from portfolio_tracker.infrastructure.persistence.sqlite.executor import (
    Row,
    SqliteExecutor,
)
from portfolio_tracker.infrastructure.persistence.sqlite.registry import FieldReference


class SqliteUserRepository(UserRepository):
    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def add(self, user: User) -> None:
        self._executor.insert(
            model=User,
            values={
                "id": user.id,
                "username": user.username,
                "password_hash": user.password_hash,
            },
        )

    def get_by_username(self, username: str) -> User | None:
        row = self._executor.select_one(
            model=User,
            filter_=FilterNode("username", Operator.EQ, username, User),
        )
        if not row:
            return None

        return self._row_to_user(row)

    def _row_to_user(self, row: Row) -> User:
        def field(name: str) -> FieldReference:
            return FieldReference(User, name)

        return User(
            id=row[field("id")],
            username=row[field("username")],
            password_hash=row[field("password_hash")],
        )
