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


class InstitutionRegistry:
    def __init__(self, institutions: dict[str, Institution]) -> None:
        self._institutions = institutions

    def get(self, institution_id: str) -> Institution:
        if institution_id not in self._institutions:
            raise ValueError(f"Institution id '{institution_id}' not found.")

        return self._institutions[institution_id]
