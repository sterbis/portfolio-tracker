from abc import ABC, abstractmethod
from dataclasses import dataclass
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
        return {name: getattr(self, name) for name in self.parameter_names()}

    @classmethod
    @abstractmethod
    def parameter_names(cls) -> tuple[str, ...]: ...

    @classmethod
    @abstractmethod
    def secret_parameter_names(cls) -> tuple[str, ...]: ...
