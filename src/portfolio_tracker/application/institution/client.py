from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Generic, TypeVar

from portfolio_tracker.domain.institution import Credentials


TCredentials = TypeVar("TCredentials", bound=Credentials)


class InstitutionClient(ABC, Generic[TCredentials]):
    _MAX_REPORT_CHUNK_DAYS: int

    def __init__(self, credentials: TCredentials) -> None:
        self._credentials = credentials

    def fetch_report(self, start: datetime, end: datetime) -> Iterator[str]:
        report_chunks: list[Iterator[str]] = []
        current_start = start

        while current_start < end:
            current_end = min(current_start + timedelta(days=self._MAX_REPORT_CHUNK_DAYS), end)
            
            report_chunk = self._fetch_report_chunk(current_start, current_end)
            report_chunks.append(report_chunk)

            current_start = current_end

        return self._merge_report_chunks(report_chunks)
    
    @abstractmethod
    def _fetch_report_chunk(self, start: datetime, end: datetime) -> Iterator[str]: ...

    @abstractmethod
    def _merge_report_chunks(self, chunks: list[Iterator[str]]) -> Iterator[str]: ...


class InstitutionClientError(Exception): ...
