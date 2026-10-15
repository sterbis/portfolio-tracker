import asyncio
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator

import requests

from portfolio_tracker.application.institution import InstitutionClient, ReportChunk
from portfolio_tracker.application.shared.errors import InstitutionClientError
from portfolio_tracker.domain.institution import Credentials
from portfolio_tracker.shared.requests_utils import (
    ApiEndpoint,
    HttpMethod,
    RateLimit,
    async_request,
    sync_request,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Trading212Credentials(Credentials):
    account_id: str
    api_key: str
    api_secret: str

    @classmethod
    def parameter_names(cls) -> tuple[str, ...]:
        return ("account_id", "api_key", "api_secret")

    @classmethod
    def secret_parameter_names(cls) -> tuple[str, ...]:
        return ("api_secret",)


class Trading212ApiEndpoints:
    REQUEST_REPORT = ApiEndpoint(
        path="equity/history/exports",
        method=HttpMethod.POST,
        rate_limit=RateLimit(max_requests=1, interval=30),
    )
    LIST_REPORTS = ApiEndpoint(
        path="equity/history/exports",
        method=HttpMethod.GET,
        rate_limit=RateLimit(max_requests=1, interval=60),
    )
    ACCOUNT_SUMMARY = ApiEndpoint(
        path="equity/account/summary",
        method=HttpMethod.GET,
        rate_limit=RateLimit(max_requests=1, interval=5),
    )


class Trading212Client(InstitutionClient[Trading212Credentials]):
    _BASE_URL = "https://live.trading212.com/api/v0/"
    _MAX_REPORT_DAYS = 365
    _TIMEZONE = timezone.utc

    def __init__(self, credentials: Trading212Credentials) -> None:
        super().__init__(credentials)
        self._endpoints = Trading212ApiEndpoints()

    @property
    def _auth(self) -> tuple[str, str]:
        return (self._credentials.api_key, self._credentials.api_secret)

    async def fetch_report(
        self, start: datetime, end: datetime
    ) -> AsyncIterator[ReportChunk]:
        intervals = self._get_report_chunk_intervals(start, end, self._MAX_REPORT_DAYS)
        report_ids: set[str] = set()

        for index, (chunk_start, chunk_end) in enumerate(intervals):
            report_ids.add(
                await self._request_report_generation(chunk_start, chunk_end)
            )
            if index < len(intervals) - 1:
                await asyncio.sleep(
                    self._endpoints.REQUEST_REPORT.rate_limit.retry_after_interval
                    if self._endpoints.REQUEST_REPORT.rate_limit
                    else 30
                )

        async for download_url in self._wait_for_reports_generation(report_ids):
            yield self._download_report(download_url)

    def verify_connection(self) -> None:
        try:
            sync_request(
                Trading212ApiEndpoints.ACCOUNT_SUMMARY,
                base_url=self._BASE_URL,
                auth=self._auth,
            )

        except requests.RequestException as error:
            raise InstitutionClientError(
                f"Institution connection failed: {str(error)}."
            ) from error

    async def _request_report_generation(
        self,
        start: datetime,
        end: datetime,
        dividends: bool = True,
        interest: bool = True,
        orders: bool = True,
        transactions: bool = True,
    ) -> str:
        response = await async_request(
            Trading212ApiEndpoints.REQUEST_REPORT,
            base_url=self._BASE_URL,
            auth=self._auth,
            json={
                "timeFrom": start.astimezone(self._TIMEZONE).isoformat(),
                "timeTo": end.astimezone(self._TIMEZONE).isoformat(),
                "dataIncluded": {
                    "includeDividends": dividends,
                    "includeInterest": interest,
                    "includeOrders": orders,
                    "includeTransactions": transactions,
                },
            },
        )
        return str(response.json()["reportId"])

    async def _wait_for_reports_generation(
        self,
        report_ids: set[str],
        first_try_after_interval: float = 30,
        timeout: float = 300,
    ) -> AsyncIterator[str]:
        deadline = time.time() + timeout
        await asyncio.sleep(first_try_after_interval)

        retry_after_interval = (
            self._endpoints.LIST_REPORTS.rate_limit.retry_after_interval
            if self._endpoints.LIST_REPORTS.rate_limit
            else 60
        )
        pending_report_ids = report_ids.copy()

        while pending_report_ids:
            response = await async_request(
                Trading212ApiEndpoints.LIST_REPORTS,
                base_url=self._BASE_URL,
                auth=self._auth,
            )
            for report_metadata in response.json():
                report_id = str(report_metadata["reportId"])
                if report_id not in pending_report_ids:
                    continue

                status = report_metadata["status"]
                if status == "Finished":
                    pending_report_ids.remove(report_id)
                    yield report_metadata["downloadLink"]

                if status in ("Canceled", "Failed"):
                    raise InstitutionClientError("Failed to generate report.")

            if pending_report_ids:
                if time.time() + retry_after_interval > deadline:
                    raise InstitutionClientError(
                        f"Report generation not finished within timeout: {timeout} seconds."
                    )

                await asyncio.sleep(retry_after_interval)

    def _download_report(self, url: str) -> Iterator[str]:
        try:
            response = sync_request(url, timeout=10.0, stream=True)

        except requests.RequestException as error:
            raise InstitutionClientError(
                f"Failed to download report from: {str(error)}."
            ) from error

        if response.encoding is None:
            response.encoding = "utf-8"

        try:
            for line in response.iter_lines(decode_unicode=True):
                assert isinstance(line, str)
                yield line

        finally:
            response.close()
