from abc import ABC, abstractmethod

from portfolio_tracker.domain.institution import Credentials, InstitutionRegistry


class CredentialsStore(ABC):
    def __init__(self, institution_registry: InstitutionRegistry) -> None:
        self._institution_registry = institution_registry

    @abstractmethod
    def store(self, institution_account_id: str, credentials: Credentials) -> None: ...

    @abstractmethod
    def retrieve(self, institution_account_id: str) -> Credentials | None: ...

    @abstractmethod
    def remove(self, institution_account_id: str) -> None: ...
