from .account import account_app
from .import_report import import_app
from .institution import institution_app
from .overview import overview_app
from .settings import settings_app
from .sync import sync_app
from .transaction import transaction_app
from .user import user_app

__all__ = [
    "account_app",
    "import_app",
    "institution_app",
    "overview_app",
    "settings_app",
    "sync_app",
    "transaction_app",
    "user_app",
]
