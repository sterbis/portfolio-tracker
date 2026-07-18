import asyncio

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Generic, TypeVar

from portfolio_tracker.domain.institution import Credentials


TCredentials = TypeVar("TCredentials", bound=Credentials)


class InstitutionClient(ABC, Generic[TCredentials]):
    _MAX_REPORT_DAYS: int

    def __init__(self, credentials: TCredentials) -> None:
        self._credentials = credentials

    async def fetch_report(self, start: datetime, end: datetime) -> Iterator[str]:
        tasks = []
        current_start = start
    
        while current_start < end:
            current_end = min(current_start + timedelta(days=self._MAX_REPORT_DAYS), end)
            tasks.append(self._generate_report(current_start, current_end))
            current_start = current_end

        download_urls = await asyncio.gather(*tasks)

        reports: list[Iterator[str]] = []
    
        for url in download_urls:
            reports.append(self._download_report(url))

        return self._merge_reports(reports)

    @abstractmethod
    def verify_connection(self) -> None: ...
    
    @abstractmethod
    async def _generate_report(self, start: datetime, end: datetime) -> str: ...

    @abstractmethod
    def _download_report(self, url: str) -> Iterator[str]: ...

    @abstractmethod
    def _merge_reports(self, reports: list[Iterator[str]]) -> Iterator[str]: ...
