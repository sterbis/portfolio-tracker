from abc import ABC, abstractmethod
from datetime import datetime

from portfolio_tracker.application.services.accounts import Credentials


class InstitutionClient(ABC):
    @abstractmethod
    def fetch_report(
        self, credentials: Credentials, last_sync: datetime | None
    ) -> bytes: ...
