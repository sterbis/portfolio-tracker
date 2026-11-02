from dataclasses import dataclass

from portfolio_tracker.application.container import Container
from portfolio_tracker.application.shared.errors import UserNotLoggedInError, UserAlreadyLoggedOutError
from portfolio_tracker.presentation.desktop.session import LoginSession, LoginSessionStore
from portfolio_tracker.settings import Settings
from portfolio_tracker.shared.settings_utils import SettingsCache, SettingsValidationError


ENVIRONMENT_KEY = f"{__name__}.environment"


@dataclass(frozen=True, kw_only=True)
class CliEnvironment:
    is_interactive: bool


@dataclass(kw_only=True)
class CliContext:
    current_user_id: str | None
    container: Container
    settings_cache: SettingsCache[Settings]
    session_store: LoginSessionStore
    environment: CliEnvironment

    @property
    def user_id(self) -> str:
        if self.current_user_id is None:
            raise UserNotLoggedInError()

        return self.current_user_id

    @property
    def settings(self) -> Settings:
        return self.settings_cache.get(self.current_user_id)

    @property
    def user_or_default_settings(self) -> Settings:
        try:
            return self.settings_cache.get(self.current_user_id)
        except SettingsValidationError:
            return self.settings_cache.default_settings

    def log_in(self, user_id: str) -> None:
        self.current_user_id = user_id
        self.session_store.save(
            LoginSession.start(
                user_id=user_id,
                ttl=self.user_or_default_settings.application.cli_session_ttl)
        )

    def log_out(self) -> None:
        if self.session_store.load() is None:
            raise UserAlreadyLoggedOutError()

        self.current_user_id = None
        self.session_store.clear()

    def touch_session(self) -> None:
        session = self.session_store.load()
        if session is not None:
            self.session_store.save(
                LoginSession.start(
                    user_id=session.user_id, 
                    ttl=self.user_or_default_settings.application.cli_session_ttl
                )
            )
