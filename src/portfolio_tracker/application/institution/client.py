import asyncio
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from enum import StrEnum
from typing import Any, AsyncIterator, Generic, TypeVar

import requests

from portfolio_tracker.domain.institution import Credentials

from .exceptions import InstitutionClientError

ReportChunk = Iterator[str]
TCredentials = TypeVar("TCredentials", bound=Credentials)


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
        url = endpoint.build_url(self._BASE_URL)

        for attempt in range(1, max_attempts + 1):
            try:
                response = await asyncio.to_thread(
                    requests.request,
                    method=endpoint.method.value,
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

                if attempt < max_attempts:
                    interval = self._get_retry_after_interval(
                        attempt=attempt,
                        initial_backoff=initial_backoff,
                        exponential_backoff=exponential_backoff,
                        response=error.response if status_code == 429 else None,
                        endpoint=endpoint if status_code == 429 else None,
                    )
                    await asyncio.sleep(interval)
                    continue

                raise InstitutionClientError(
                    f"Request to {url} failed after {max_attempts} attempts. "
                    f"Status: {status_code}, reason: {reason}"
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
