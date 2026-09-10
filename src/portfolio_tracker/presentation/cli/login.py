import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, TypeVar

import keyring
from keyring.errors import PasswordDeleteError

from portfolio_tracker.application.shared.errors import UserNotLoggedInError

TFunction = TypeVar("TFunction", bound=Callable[..., Any])

KEYRING_SERVICE_NAME = "portfolio-tracker"
KEYRING_ENTRY_NAME = "login-session"


@dataclass(frozen=True)
class LoginSession:
    user_id: str | None
    expiration: datetime | None

    @property
    def is_valid(self) -> bool:
        return self.user_id is not None and not self.is_expired

    @property
    def is_expired(self) -> bool:
        if self.expiration is None:
            return True

        return datetime.now(timezone.utc) >= self.expiration


class LoginSessionStore:
    def load(self) -> LoginSession:
        json_string = keyring.get_password(KEYRING_SERVICE_NAME, KEYRING_ENTRY_NAME)
        if not json_string:
            return LoginSession(user_id=None, expiration=None)

        try:
            data = json.loads(json_string)
            return LoginSession(
                user_id=data["user_id"],
                expiration=datetime.fromisoformat(data["expiration"]),
            )
        except json.JSONDecodeError, KeyError, ValueError, TypeError:
            return LoginSession(user_id=None, expiration=None)

    def save(self, user_id: str, session_ttl: int) -> LoginSession:
        expiration = datetime.now(timezone.utc) + timedelta(seconds=session_ttl)
        data = {"user_id": user_id, "expiration": expiration.isoformat()}
        keyring.set_password(KEYRING_SERVICE_NAME, KEYRING_ENTRY_NAME, json.dumps(data))
        return LoginSession(user_id, expiration)

    def extend(self, session: LoginSession, session_ttl: int) -> LoginSession:
        if session.user_id is None:
            raise UserNotLoggedInError()

        return self.save(session.user_id, session_ttl)

    def clear(self) -> None:
        try:
            keyring.delete_password(KEYRING_SERVICE_NAME, KEYRING_ENTRY_NAME)

        except PasswordDeleteError:
            pass
