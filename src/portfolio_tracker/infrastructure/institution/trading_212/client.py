import asyncio
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import requests

from portfolio_tracker.application.institution import (
    ApiEndpoint,
    HttpMethod,
    InstitutionClient,
    RateLimit,
    ReportChunk,
)
from portfolio_tracker.application.shared.errors import InstitutionClientError
from portfolio_tracker.domain.institution import Credentials

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
        self._auth = (self._credentials.api_key, self._credentials.api_secret)

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
                    Trading212ApiEndpoints.REQUEST_REPORT.rate_limit.retry_after_interval
                )

        reports_metadata = await self._wait_for_reports_generation(report_ids)

        for report_metadata in reports_metadata:
            yield self._download_report(report_metadata["downloadLink"])

    def verify_connection(self) -> None:
        endpoint = Trading212ApiEndpoints.ACCOUNT_SUMMARY
        method = endpoint.method
        url = endpoint.build_url(self._BASE_URL)
        try:
            logger.debug("Sending request:\nMethod: %s\nURL: %s\n", method, url)
            requests.get(url, auth=self._auth, timeout=5).raise_for_status()

        except requests.RequestException as error:
            logger.debug(
                "%s request to '%s' failed. Status code: %s. Reason: %s",
                method,
                url,
                error.response.status_code if error.response else "Unknown",
                error.response.reason if error.response else "Unknown",
            )
            raise InstitutionClientError(f"Request to '{url}' failed.") from error

    def _download_report(self, url: str) -> Iterator[str]:
        method = "GET"
        try:
            logger.debug("Sending request:\nMethod: %s\nURL: %s\n", method, url)
            response = requests.request(method, url, timeout=10.0, stream=True)
            response.raise_for_status()
        except requests.RequestException as error:
            logger.debug(
                "%s request to '%s' failed. Status code: %s. Reason: %s",
                method,
                url,
                error.response.status_code if error.response else "Unknown",
                error.response.reason if error.response else "Unknown",
            )
            raise InstitutionClientError(
                f"Failed to download report from '{url}'."
            ) from error

        if response.encoding is None:
            response.encoding = "utf-8"

        try:
            for line in response.iter_lines(decode_unicode=True):
                assert isinstance(line, str)
                yield line

        finally:
            response.close()

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
