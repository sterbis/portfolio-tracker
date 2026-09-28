from dataclasses import dataclass, field

from portfolio_tracker.shared.id_utils import generate_random_hex_id


@dataclass(frozen=True, kw_only=True)
class User:
    id: str = field(default_factory=lambda: generate_random_hex_id(prefix="usr"))
    username: str
    password_hash: str
