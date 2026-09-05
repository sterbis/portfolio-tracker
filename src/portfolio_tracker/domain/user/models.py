import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True)
class User:
    id: str = field(default_factory=lambda: f"usr_{uuid.uuid4().hex[:16]}")
    username: str
    password_hash: str
