from dataclasses import dataclass

from portfolio_tracker.domain.user import User


@dataclass(frozen=True)
class UserView:
    id: str
    username: str

    @classmethod
    def from_domain(cls, user: User) -> UserView:
        return cls(
            id=user.id,
            username=user.username,
        )
