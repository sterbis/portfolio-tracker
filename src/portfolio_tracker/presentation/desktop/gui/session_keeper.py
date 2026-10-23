from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, QTimer

from portfolio_tracker.presentation.desktop.session import LoginSession, LoginSessionStore
from portfolio_tracker.settings import Settings



@dataclass(frozen=True)
class LoginSessionPolicy:
    ttl: int
    touch_interval: int

    @classmethod
    def from_settings(cls, settings: Settings) -> LoginSessionPolicy:
        return cls(
            ttl=settings.application.gui_session_ttl,
            touch_interval=settings.application.gui_session_touch_interval,
        )


class LoginSessionKeeper(QObject):
    def __init__(
        self, user_id: str,
        store: LoginSessionStore,
        policy: Callable[[], LoginSessionPolicy],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._user_id = user_id
        self._store = store
        self._policy = policy
        self._is_active = True

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.touch) # pylint: disable=no-member

    def touch(self) -> None:
        if not self._is_active:
            return

        policy = self._policy()
        try:
            self._store.save(LoginSession.start(self._user_id, policy.ttl))
        finally:
            self._timer.start(policy.touch_interval * 1000)

    def stop(self) -> None:
        self._is_active = False
        self._timer.stop()
        self._store.clear()

    def clear(self) -> None:
        self.stop()
        self._store.clear()
