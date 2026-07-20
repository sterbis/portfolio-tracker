import asyncio
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator

import requests

from portfolio_tracker.application.institution import (
    ApiEndpoint,
    HttpMethod,
    InstitutionClient,
    InstitutionClientError,
    RateLimit,
    ReportChunk,
)
from portfolio_tracker.domain.institution import Credentials


@dataclass(frozen=True)
class Trading212Credentials(Credentials):
    api_key: str
    api_secret: str


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
        self._auth = (self._credentials.api_key, self._credentials.api_secret)

    async def fetch_report(
        self, start: datetime, end: datetime
    ) -> AsyncIterator[ReportChunk]:
        report_ids: set[str] = set()
        current_start = start

        while current_start < end:
            current_end = min(
                current_start + timedelta(days=self._MAX_REPORT_DAYS), end
            )
            report_ids.add(
                await self._request_report_generation(current_start, current_end)
            )
            await asyncio.sleep(
                Trading212ApiEndpoints.REQUEST_REPORT.rate_limit.retry_after_interval
            )
            current_start = current_end

        reports_metadata = await self._wait_for_reports_generation(report_ids)

        for report_metadata in reports_metadata:
            yield self._download_report(report_metadata["downloadLink"])

    def verify_connection(self) -> None:
        url = Trading212ApiEndpoints.ACCOUNT_SUMMARY.build_url(self._BASE_URL)
        try:
            requests.get(url, auth=self._auth, timeout=5).raise_for_status()

        except requests.RequestException as error:
            raise InstitutionClientError(f"Request to '{url}' failed.") from error

    def _download_report(self, url: str) -> Iterator[str]:
        try:
            response = requests.request("GET", url, timeout=10.0, stream=True)
            response.raise_for_status()
        except requests.RequestException as error:
            raise InstitutionClientError(
                f"Failed to download report from '{url}'."
            ) from error

        for line in response.iter_lines(decode_unicode=True):
            assert isinstance(line, str)
            yield line

    async def _request_report_generation(
        self,
        start: datetime,
        end: datetime,
        dividends: bool = True,
        interest: bool = True,
        orders: bool = True,
        transactions: bool = True,
    ) -> str:
        response = await self._request(
            endpoint=Trading212ApiEndpoints.REQUEST_REPORT,
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
    ) -> list[dict[str, Any]]:
        await asyncio.sleep(first_try_after_interval)

        retry_after_interval = (
            Trading212ApiEndpoints.LIST_REPORTS.rate_limit.retry_after_interval
        )
        deadline = time.time() + timeout

        while True:
            try:
                metadata_list = await self._fetch_reports_metadata(report_ids)
            except InstitutionClientError:
                metadata_list = []

            if all(metadata.get("status") == "Finished" for metadata in metadata_list):
                return metadata_list

            if time.time() + retry_after_interval > deadline:
                raise InstitutionClientError(
                    f"Report generation not finished within timeout: {timeout} seconds."
                )

            await asyncio.sleep(retry_after_interval)

    async def _fetch_reports_metadata(
        self, report_ids: set[str]
    ) -> list[dict[str, Any]]:
        response = await self._request(
            endpoint=Trading212ApiEndpoints.LIST_REPORTS,
            auth=self._auth,
        )
        metadata_list: list[dict[str, Any]] = [
            metadata
            for metadata in response.json()
            if str(metadata["reportId"]) in report_ids
        ]
        if missing_ids := report_ids - {
            str(metadata["reportId"]) for metadata in metadata_list
        }:
            raise InstitutionClientError(
                f"Following report ids not found: {', '.join(missing_ids)}."
            )

        return metadata_list
