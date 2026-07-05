import json
from dataclasses import asdict

from portfolio_tracker.domain.institution import Credentials, Institution


def serialize_credentials(credentials: Credentials) -> str:
    return json.dumps(asdict(credentials))


def deserialize_credentials(institution: Institution, plain_text: str) -> Credentials:
    credentials_cls = institution.credentials_cls
    return credentials_cls(**json.loads(plain_text))
