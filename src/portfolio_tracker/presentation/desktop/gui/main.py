import logging
import sys

from PySide6.QtWidgets import QApplication, QDialog

from portfolio_tracker.application.user import UserService
from portfolio_tracker.infrastructure.configuration import APP_NAME, load_configuration
from portfolio_tracker.infrastructure.logging import configure_logging
from portfolio_tracker.infrastructure.keyring_session_store import (
    KeyringLoginSessionStore,
)
from portfolio_tracker.bootstrap import bootstrap
from portfolio_tracker.presentation.desktop.session import LoginSessionStore
from portfolio_tracker.shared.settings_utils import SettingsCache
from portfolio_tracker.settings import Settings

from .auth_dialog import AuthDialog
from .context import GuiContext
from .exception_handler import install_exception_handler
from .main_window import MainWindow
from .market_data_feed import MarketDataFeed
from .session_keeper import LoginSessionKeeper, LoginSessionPolicy
from .tasks import TaskRunner

print(__name__)
logger = logging.getLogger(__name__)

SESSION_STORE_SERVICE_NAME = "portfolio-tracker"
SESSION_STORE_ENTRY_NAME = "gui-login-session"


def main() -> int:
    logger.info("PortfolioTracker running...")
    app = QApplication(sys.argv)
    app.setOrganizationName(APP_NAME)
    app.setApplicationName(APP_NAME)

    configuration = load_configuration()
    log_file = configure_logging(configuration)
    install_exception_handler(app, log_file)
    container, settings_cache = bootstrap(configuration)

    session_store = create_session_store()
    user_id = resolve_user(container.user_service, session_store)
    if user_id is None:
        logger.info("Login cancelled, exiting.")
        return 0

    settings = settings_cache.get(user_id)
    session_keeper = start_session_keeper(user_id, app, session_store, settings_cache)
    task_runner = TaskRunner(app)
    market_data_feed = MarketDataFeed(
        task_runner=task_runner,
        fx_service=container.fx_service,
        market_data_service=container.market_data_service,
        interval=settings.application.market_data.refresh_interval,
        parent=app,
    )

    window = MainWindow(
        context=GuiContext(
            user_id=user_id,
            container=container,
            market_data_feed=market_data_feed,
            task_runner=task_runner,
            settings_cache=settings_cache,
            session_keeper=session_keeper,
        )
    )
    window.show()

    return app.exec()


def create_session_store() -> LoginSessionStore:
    return KeyringLoginSessionStore(
        SESSION_STORE_SERVICE_NAME, SESSION_STORE_ENTRY_NAME
    )


def resolve_user(user_service: UserService, store: LoginSessionStore) -> str | None:
    session = store.load()
    if session is not None:
        if not session.is_expired() and user_service.exists(session.user_id):
            return session.user_id

        store.clear()

    dialog = AuthDialog(user_service)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    return dialog.get_logged_in_user_id()


def start_session_keeper(
    user_id: str,
    app: QApplication,
    store: LoginSessionStore,
    settings_cache: SettingsCache[Settings],
) -> LoginSessionKeeper:
    keeper = LoginSessionKeeper(
        user_id,
        store,
        policy_factory=lambda: LoginSessionPolicy.from_settings(settings_cache.get(user_id)),
        parent=app,
    )
    keeper.touch()
    app.aboutToQuit.connect(keeper.touch)  # pylint: disable=no-member
    return keeper
