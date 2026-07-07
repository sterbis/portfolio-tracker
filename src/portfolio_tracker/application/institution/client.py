from abc import ABC, abstractmethod
from datetime import datetime

from portfolio_tracker.domain.institution import Credentials


class InstitutionClient(ABC):
    @abstractmethod
    def fetch_report(
        self, credentials: Credentials, last_synced_at: datetime | None
    ) -> bytes: ...
