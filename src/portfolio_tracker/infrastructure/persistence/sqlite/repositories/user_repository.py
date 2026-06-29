from filterutils import FilterNode, Operator

from portfolio_tracker.application.ports.repositories import UserRepository
from portfolio_tracker.domain.user import User

from ..executor import SqliteExecutor


class SqliteUserRepository(UserRepository):
    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def add(self, user: User) -> None:
        self._executor.insert(
            table="user",
            values={
                "user_id": user.id,
                "username": user.username,
                "password_hash": user.password_hash,
            },
        )

    def get_by_username(self, username: str) -> User | None:
        row = self._executor.select_one(
            table="user",
            columns=["user_id", "username", "password_hash"],
            filter_=FilterNode("username", Operator.EQ, username),
        )
        if not row:
            return None

        return User(
            id=row["user_id"],
            username=row["username"],
            password_hash=row["password_hash"],
        )
