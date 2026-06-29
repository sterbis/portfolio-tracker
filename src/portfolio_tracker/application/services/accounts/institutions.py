import json
from abc import ABC
from dataclasses import asdict, dataclass
from typing import Self


@dataclass(frozen=True)
class Credentials(ABC):
    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_string: str) -> Self:
        return cls(**json.loads(json_string))


@dataclass(frozen=True)
class Trading212Credentials(Credentials):
    account_id: str
    api_key: str
    api_secret: str


@dataclass(frozen=True)
class IbkrCredentials(Credentials):
    flex_web_service_token: str
    flex_query_ids: list[str]


@dataclass(frozen=True)
class Institution:
    id: str
    name: str
    log_in_url: str
    credentials: type[Credentials]


SUPPORTED_INSTITUTIONS: dict[str, Institution] = {
    "T212": Institution(
        id="T212",
        name="Trading 212",
        log_in_url="https://www.trading212.com",
        credentials=Trading212Credentials,
    ),
    "IBKR": Institution(
        id="IBKR",
        name="Interactive Brokers",
        log_in_url="https://www.interactivebrokers.com",
        credentials=IbkrCredentials,
    ),
}
