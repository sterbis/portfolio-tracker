import json
from dataclasses import asdict
from typing import Any

from portfolio_tracker.domain.institution import Credentials


def serialize_credentials(credentials: Credentials) -> str:
    return json.dumps(asdict(credentials))


def deserialize_credentials(plain_text: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(plain_text)
    return data
