import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import keyring
from keyring.errors import PasswordDeleteError

from portfolio_tracker.application.shared.errors import UserNotLoggedInError


SERVICE_NAME = "portfolio-tracker"
USERNAME = "session"


@dataclass(frozen=True)
class UserSession:
    user_id: str | None
    expiration: datetime | None

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None and not self.is_expired

    @property
    def is_expired(self) -> bool:
        if self.expiration is None:
            return True

        return datetime.now(timezone.utc) >= self.expiration

    def refresh(self, session_ttl: int) -> UserSession:
        if self.user_id is None:
            raise UserNotLoggedInError()

        return self.create(self.user_id, session_ttl)

    def clear(self) -> UserSession:
        try:
            keyring.delete_password(SERVICE_NAME, USERNAME)

        except PasswordDeleteError:
            pass

        return UserSession(user_id=None, expiration=None)

    @classmethod
    def create(cls, user_id: str, session_ttl: int) -> UserSession:
        expiration = datetime.now(timezone.utc) + timedelta(seconds=session_ttl)
        data = {
            "user_id": user_id,
            "expiration": expiration,
        }
        keyring.set_password(SERVICE_NAME, USERNAME, json.dumps(data))
        return UserSession(user_id, expiration)

    @classmethod
    def get(cls) -> UserSession:
        json_string = keyring.get_password(SERVICE_NAME, USERNAME)
        if not json_string:
            return UserSession(user_id=None, expiration=None)

        data = json.loads(json_string)
        return UserSession(
            user_id=data["user_id"],
            expiration=datetime.fromtimestamp(data["expiration"], tz=timezone.utc),
        )
