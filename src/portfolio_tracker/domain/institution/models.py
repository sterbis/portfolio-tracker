from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class Credentials(ABC):
    pass


@dataclass(frozen=True)
class Institution:
    id: str
    name: str
    log_in_url: str
    credentials_cls: type[Credentials]
