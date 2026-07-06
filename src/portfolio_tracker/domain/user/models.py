import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    username: str
    password_hash: str
    id: str = field(default_factory=lambda: f"usr_{uuid.uuid4().hex[:16]}")
