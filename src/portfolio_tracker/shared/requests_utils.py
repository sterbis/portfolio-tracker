import asyncio
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from enum import StrEnum
from pprint import pformat
from typing import Any

import requests

ReportChunk = Iterator[str]

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


async def async_request(
    endpoint: ApiEndpoint | str,
    *,
    base_url: str | None = None,
    method: HttpMethod = HttpMethod.GET,
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
    url, method, rate_limit = _resolve_target(
        endpoint, base_url=base_url, method=method
    )

    for attempt in range(1, max_attempts + 1):
        _log_request(method, url, headers=headers, params=params, json=json)
        try:
            response = await asyncio.to_thread(
                requests.request,
                method=method.value,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=headers,
                auth=auth,
                timeout=timeout,
            )
            response.raise_for_status()
            _log_response_success(method, url, response)
            return response

        except requests.RequestException as error:
            _log_response_failure(method, url, error)
            if attempt >= max_attempts:
                raise

            status_code = error.response.status_code if error.response else None
            interval = _get_retry_after_interval(
                attempt=attempt,
                initial_backoff=initial_backoff,
                exponential_backoff=exponential_backoff,
                response=error.response if status_code == 429 else None,
                rate_limit=rate_limit if status_code == 429 else None,
            )
            logger.debug("Retrying after %s seconds...", interval)
            await asyncio.sleep(interval)

    raise AssertionError("unreachable")


def sync_request(
    endpoint: ApiEndpoint | str,
    *,
    base_url: str | None = None,
    method: HttpMethod = HttpMethod.GET,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    auth: tuple[str, str] | None = None,
    timeout: float = 5.0,
    stream: bool = False,
    max_attempts: int = 3,
    initial_backoff: float = 5.0,
    exponential_backoff: bool = True,
) -> requests.Response:
    url, method, rate_limit = _resolve_target(
        endpoint, base_url=base_url, method=method
    )

    for attempt in range(1, max_attempts + 1):
        _log_request(method, url, headers=headers, params=params, json=json)
        try:
            response = requests.request(
                method=method.value,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=headers,
                auth=auth,
                timeout=timeout,
                stream=stream,
            )
            response.raise_for_status()
            _log_response_success(method, url, response)
            return response

        except requests.RequestException as error:
            _log_response_failure(method, url, error)
            if attempt >= max_attempts:
                raise

            status_code = error.response.status_code if error.response else None
            interval = _get_retry_after_interval(
                attempt=attempt,
                initial_backoff=initial_backoff,
                exponential_backoff=exponential_backoff,
                response=error.response if status_code == 429 else None,
                rate_limit=rate_limit if status_code == 429 else None,
            )
            logger.debug("Retrying after %s seconds...", interval)
            time.sleep(interval)

    raise AssertionError("unreachable")


def _resolve_target(
    target: ApiEndpoint | str,
    *,
    base_url: str | None,
    method: HttpMethod,
) -> tuple[str, HttpMethod, RateLimit | None]:
    if isinstance(target, ApiEndpoint):
        if base_url is None:
            raise ValueError("base_url is required when target is an ApiEndpoint.")

        return target.build_url(base_url), target.method, target.rate_limit

    return target, method, None


def _log_request(
    method: HttpMethod, url: str, *, headers: Any, params: Any, json: Any
) -> None:
    logger.debug(
        "Sending request.\nMethod: %s\nURL: %s\nHeaders: %s\nParameters: %s\nJSON: %s\n",
        method.value,
        url,
        pformat(headers, sort_dicts=False),
        pformat(params, sort_dicts=False),
        pformat(json, sort_dicts=False),
    )


def _log_response_success(
    method: HttpMethod, url: str, response: requests.Response
) -> None:
    logger.debug(
        "Request succeeded.\nMethod: %s\nURL: %s\nStatus code: %s\nContent-Type: %s\nContent-Length: %s\n",
        method.value,
        url,
        response.status_code,
        response.headers.get("Content-Type", "Unknown"),
        response.headers.get("Content-Length", "Unknown"),
    )


def _log_response_failure(
    method: HttpMethod, url: str, error: requests.RequestException
) -> None:
    status_code = error.response.status_code if error.response else "Unknown"
    reason = error.response.reason if error.response else "Unknown"
    logger.debug(
        "Request failed.\nMethod: %s\nURL: %s\nStatus code: %s\nReason: %s\n",
        method.value,
        url,
        status_code,
        reason,
    )


def _get_retry_after_interval(
    attempt: int,
    initial_backoff: float,
    exponential_backoff: bool = True,
    response: requests.Response | None = None,
    rate_limit: RateLimit | None = None,
) -> float:
    if response and response.headers.get("Retry-After"):
        retry_after = response.headers["Retry-After"]
        try:
            return max(float(retry_after), 0.0)
        except ValueError:
            pass
        try:
            retry_at = parsedate_to_datetime(retry_after)
            return max((retry_at - datetime.now(tz=timezone.utc)).total_seconds(), 0.0)
        except ValueError, TypeError:
            pass

    if rate_limit:
        return rate_limit.retry_after_interval

    if exponential_backoff:
        return float(initial_backoff * (2 ** (attempt - 1)))

    return initial_backoff
