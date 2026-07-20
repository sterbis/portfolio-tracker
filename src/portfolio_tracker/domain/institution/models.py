from abc import ABC
from dataclasses import dataclass
from enum import StrEnum


class InstitutionId(StrEnum): ...


@dataclass(frozen=True)
class Credentials(ABC):
    pass


@dataclass(frozen=True)
class Institution:
    id: InstitutionId
    name: str
    log_in_url: str
    credentials_cls: type[Credentials]
