from abc import ABC
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class InstitutionId(StrEnum): ...


@dataclass(frozen=True)
class Institution:
    id: InstitutionId
    name: str
    log_in_url: str


@dataclass(frozen=True)
class Credentials(ABC):
    institution_id: InstitutionId
    institution_account_id: str

    @property
    def parameters(self) -> dict[str, Any]:
        parameters = asdict(self)
        parameters.pop("institution_id")
        parameters.pop("institution_account_id")
        return parameters
