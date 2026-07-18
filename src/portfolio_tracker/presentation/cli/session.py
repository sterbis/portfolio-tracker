import time

import keyring
from keyring.errors import PasswordDeleteError


def set_login_session(user_id: str, session_ttl: int) -> None:
    session_expiration = int(time.time()) + session_ttl
    keyring.set_password(
        "portfolio-tracker", "active_user", f"{user_id}|{session_expiration}"
    )


def get_login_session() -> tuple[str | None, int | None]:
    active_user = keyring.get_password("portfolio-tracker", "active_user")
    if active_user:
        active_user_id, session_expiration = active_user.split("|")
        return active_user_id, int(session_expiration)

    return None, None


def delete_login_session() -> bool:
    try:
        keyring.delete_password("portfolio-tracker", "active_user")
        return True

    except PasswordDeleteError:
        return False
