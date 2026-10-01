from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import AsyncIterator, Generic, TypeVar

from portfolio_tracker.domain.institution import Credentials

ReportChunk = Iterator[str]
TCredentials = TypeVar("TCredentials", bound=Credentials)


class InstitutionClient(ABC, Generic[TCredentials]):
    def __init__(self, credentials: TCredentials) -> None:
        self._credentials = credentials

    @abstractmethod
    async def fetch_report(
        self, start: datetime, end: datetime
    ) -> AsyncIterator[ReportChunk]:
        yield ("" for _ in range(0))

    @abstractmethod
    def verify_connection(self) -> None: ...

    def _get_report_chunk_intervals(
        self, start: datetime, end: datetime, max_chunk_days: int
    ) -> list[tuple[datetime, datetime]]:
        intervals: list[tuple[datetime, datetime]] = []
        current_start = start
        while current_start < end:
            current_end = min(current_start + timedelta(days=max_chunk_days), end)
            intervals.append((current_start, current_end))
            current_start = current_end

        return intervals
