import json
import logging
from datetime import datetime

import keyring
from keyring.errors import KeyringError, PasswordDeleteError, PasswordSetError

from portfolio_tracker.presentation.desktop.session import LoginSession, LoginSessionStore

logger = logging.getLogger(__name__)


class KeyringLoginSessionStore(LoginSessionStore):
    def __init__(self, service_name: str, entry_name: str) -> None:
        self._service_name = service_name
        self._entry_name = entry_name

    def load(self) -> LoginSession | None:
        try:
            json_string = keyring.get_password(self._service_name, self._entry_name)
            if not json_string:
                return None

            data = json.loads(json_string)
            return LoginSession(
                user_id=data["user_id"],
                expires_at=datetime.fromisoformat(data["expires_at"]),
            )
        except (KeyringError, json.JSONDecodeError, KeyError, ValueError, TypeError):
            logger.exception("Failed to load login session from keyring.")
            self.clear()
            return None

    def save(self, session: LoginSession) -> None:
        data = {"user_id": session.user_id, "expires_at": session.expires_at.isoformat()}
        try:
            keyring.set_password(self._service_name, self._entry_name, json.dumps(data))
        except PasswordSetError:
            logger.exception("Failed to save login session from keyring.")

    def clear(self) -> None:
        try:
            keyring.delete_password(self._service_name, self._entry_name)
        except PasswordDeleteError:
            logger.exception("Failed to clear login session from keyring.")
