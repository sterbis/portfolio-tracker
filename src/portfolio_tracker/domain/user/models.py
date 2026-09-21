import secrets
from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True)
class User:
    id: str = field(default_factory=lambda: f"usr_{secrets.token_urlsafe(8)}")
    username: str
    password_hash: str
