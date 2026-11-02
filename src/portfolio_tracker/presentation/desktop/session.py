from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class LoginSession:
    user_id: str
    expires_at: datetime

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    @classmethod
    def start(cls, user_id: str, ttl: int) -> LoginSession:
        expiration = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        return cls(user_id, expiration)


class LoginSessionStore(ABC):
    @abstractmethod
    def load(self) -> LoginSession | None: ...

    @abstractmethod
    def save(self, session: LoginSession) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...
 