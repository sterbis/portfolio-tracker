import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from enum import StrEnum
from pprint import pformat
from typing import Any, AsyncIterator, Generic, TypeVar

import requests

from portfolio_tracker.application.shared.errors import InstitutionClientError
from portfolio_tracker.domain.institution import Credentials

ReportChunk = Iterator[str]
TCredentials = TypeVar("TCredentials", bound=Credentials)

logger = logging.getLogger(__name__)


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"


@dataclass(frozen=True)
class RateLimit:
    max_requests: int
    interval: float

    @property
    def retry_after_interval(self) -> float:
        return self.interval / self.max_requests


@dataclass(frozen=True)
class ApiEndpoint:
    path: str
    method: HttpMethod
    rate_limit: RateLimit

    def build_url(self, base_url: str) -> str:
        return f"{base_url.rstrip('/')}/{self.path.lstrip('/')}"


class InstitutionClient(ABC, Generic[TCredentials]):
    _BASE_URL: str

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

    async def _request(
        self,
        endpoint: ApiEndpoint,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        auth: tuple[str, str] | None = None,
        timeout: float = 5.0,
        max_attempts: int = 3,
        initial_backoff: float = 5.0,
        exponential_backoff: bool = True,
    ) -> requests.Response:
        method = endpoint.method.value
        url = endpoint.build_url(self._BASE_URL)

        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug(
                    "Sending request.\n"
                    "Method: %s\n"
                    "URL: %s\n"
                    "Headers: %s\n"
                    "Parameters: %s\n"
                    "JSON: %s\n",
                    method,
                    url,
                    pformat(headers, sort_dicts=False),
                    pformat(params, sort_dicts=False),
                    pformat(json, sort_dicts=False),
                )
                response = await asyncio.to_thread(
                    requests.request,
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    data=data,
                    headers=headers,
                    auth=auth,
                    timeout=timeout,
                )
                response.raise_for_status()
                return response

            except requests.RequestException as error:
                status_code = (
                    error.response.status_code if error.response else "Unknown"
                )
                reason = error.response.reason if error.response else "Unknown"
                logger.debug(
                    "Request failed.\n"
                    "Method: %s\n"
                    "URL: %s\n"
                    "Status code: %s\n"
                    "Reason: %s\n",
                    method,
                    url,
                    status_code,
                    reason,
                )

                if attempt < max_attempts:
                    interval = self._get_retry_after_interval(
                        attempt=attempt,
                        initial_backoff=initial_backoff,
                        exponential_backoff=exponential_backoff,
                        response=error.response if status_code == 429 else None,
                        endpoint=endpoint if status_code == 429 else None,
                    )
                    logger.debug("Retry request after %s seconds", interval)
                    await asyncio.sleep(interval)
                    continue

                raise InstitutionClientError(
                    f"{method} request to {url} failed after {max_attempts} attempts. "
                    f"Status code: {status_code}, reason: {reason}"
                ) from error

        raise RuntimeError("Never")

    def _get_retry_after_interval(
        self,
        attempt: int,
        initial_backoff: float,
        exponential_backoff: bool = True,
        response: requests.Response | None = None,
        endpoint: ApiEndpoint | None = None,
    ) -> float:
        if response and response.headers.get("Retry-After"):
            retry_after = response.headers["Retry-After"]

            try:
                return max(float(retry_after), 0.0)
            except ValueError:
                pass

            try:
                retry_at = parsedate_to_datetime(retry_after)
                now = datetime.now(tz=timezone.utc)
                return max((retry_at - now).total_seconds(), 0.0)
            except ValueError, TypeError:
                pass

        if endpoint:
            return endpoint.rate_limit.retry_after_interval

        if exponential_backoff:
            return float(initial_backoff * (2 ** (attempt - 1)))

        return initial_backoff
