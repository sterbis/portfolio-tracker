import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import StrEnum
from typing import Any


class InstitutionId(StrEnum): ...


@dataclass(frozen=True, kw_only=True)
class Institution:
    id: InstitutionId
    name: str
    log_in_url: str


@dataclass(frozen=True, kw_only=True)
class InstitutionConnection:
    id: str = field(default_factory=lambda: f"conn_{secrets.token_urlsafe(8)}")
    institution_id: InstitutionId
    user_id: str
    name: str
    account_opened_on: date
    last_synced_at: datetime | None = None

    def with_last_synced_at(self, last_synced_at: datetime) -> InstitutionConnection:
        return replace(self, last_synced_at=last_synced_at)


@dataclass(frozen=True)
class Credentials(ABC):
    institution_id: InstitutionId
    institution_connection_id: str

    @property
    def parameters(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.parameter_names()}

    @classmethod
    @abstractmethod
    def parameter_names(cls) -> tuple[str, ...]: ...

    @classmethod
    @abstractmethod
    def secret_parameter_names(cls) -> tuple[str, ...]: ...
