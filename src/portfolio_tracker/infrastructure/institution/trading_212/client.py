import asyncio
import csv
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from io import StringIO
from itertools import tee
from typing import Any, Literal
from urllib.parse import urljoin

import requests

from portfolio_tracker.application.institution import (
    InstitutionClient,
    InstitutionClientError,
)
from portfolio_tracker.domain.institution import Credentials


@dataclass(frozen=True)
class Trading212Credentials(Credentials):
    api_key: str
    api_secret: str


class Trading212ApiEndpoint(StrEnum):
    ACCOUNT_SUMMARY = "equity/account/summary"
    ORDERS = "equity/history/orders"
    PENDING_ORDERS = "equity/orders"
    POSITIONS = "equity/positions"
    REPORTS = "equity/history/exports"
    TRANSACTIONS = "equity/history/transactions"


class Trading212Client(InstitutionClient[Trading212Credentials]):
    _BASE_URL = "https://live.trading212.com/api/v0/"
    _MAX_REPORT_DAYS = 365
    _TIMEZONE = timezone.utc

    def __init__(self, credentials: Trading212Credentials) -> None:
        super().__init__(credentials)

    def verify_connection(self) -> None:
        url = self._get_endpoint_url(Trading212ApiEndpoint.ACCOUNT_SUMMARY)
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()

        except requests.RequestException as error:
            raise InstitutionClientError(f"Request to {url} failed.") from error

    def _download_report(self, url: str) -> Iterator[str]:
        response = requests.request("GET", url, timeout=10.0, stream=True)
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                yield str(line)

    def _merge_reports(self, reports: list[Iterator[str]]) -> Iterator[str]:
        header_columns: list[str] = []

        header_streams: list[Iterator[str]] = []
        row_streams: list[Iterator[str]] = []

        for report in reports:
            header_stream, row_stream = tee(report)
            header_streams.append(header_stream)
            row_streams.append(row_stream)

        for header_stream in header_streams:
            reader = csv.DictReader(header_stream)
            if reader.fieldnames is None:
                raise InstitutionClientError("Report does not contain header row.")

            for column in reader.fieldnames:
                if column not in header_columns:
                    header_columns.append(column)

        merged_report = StringIO(newline=None)

        writer = csv.DictWriter(merged_report, fieldnames=header_columns, restval="")
        writer.writeheader()

        for row_stream in row_streams:
            reader = csv.DictReader(row_stream)
            for row in reader:
                writer.writerow(row)

        merged_report.seek(0)
        return merged_report

    async def _generate_report(self, start: datetime, end: datetime) -> str:
        report_id = await self._request_report_generation(start, end)
        report_metadata = await self._wait_for_report_generation(report_id)
        download_url: str = report_metadata["downloadLink"]
        return download_url

    async def _request_report_generation(
        self,
        start: datetime,
        end: datetime,
        dividends: bool = True,
        interest: bool = True,
        orders: bool = True,
        transactions: bool = True,
    ) -> int:
        response = await self._request(
            method="POST",
            endpoint=Trading212ApiEndpoint.REPORTS,
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
        return int(response.json()["reportId"])

    async def _wait_for_report_generation(
        self,
        report_id: int,
        timeout: float = 300,
        initial_delay: float = 30,
        poll_interval: float = 60,
    ) -> dict[str, Any]:
        await asyncio.sleep(initial_delay)

        deadline = time.time() + timeout

        while True:
            try:
                metadata = await self._fetch_report_metadata(report_id)
            except InstitutionClientError:
                metadata = {}

            if metadata.get("status") == "Finished":
                return metadata

            if time.time() + poll_interval > deadline:
                raise InstitutionClientError(
                    f"Report {report_id} generation not finished within timeout: {timeout} seconds."
                )

            await asyncio.sleep(poll_interval)

    async def _fetch_report_metadata(self, report_id: int) -> dict[str, Any]:
        response = await self._request(
            method="GET",
            endpoint=Trading212ApiEndpoint.REPORTS,
            max_attempts=1,
            exponential_backoff=False,
        )

        reports_metadata: list[dict[str, Any]] = response.json()

        for metadata in reports_metadata:
            if int(metadata["reportId"]) == report_id:
                return metadata

        raise InstitutionClientError(f"Report with id {report_id} not found.")

    async def _request(
        self,
        method: Literal["GET", "POST"],
        endpoint: Trading212ApiEndpoint,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 5.0,
        max_attempts: int = 3,
        initial_backoff: float = 5.0,
        exponential_backoff: bool = True,
    ) -> requests.Response:
        url = self._get_endpoint_url(endpoint)
        auth = (self._credentials.api_key, self._credentials.api_secret)

        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                    headers=headers,
                    auth=auth,
                    timeout=timeout,
                )
                if response.status_code == 429 and attempt < max_attempts:
                    retry_after = self._get_retry_after_duration(
                        response, attempt, initial_backoff, exponential_backoff
                    )

                    await asyncio.sleep(retry_after)

                    attempt += 1
                    continue

                response.raise_for_status()
                return response

            except requests.HTTPError as error:
                raise InstitutionClientError(
                    f"Request to {url} failed: {response.status_code} {response.reason}."
                ) from error

            except Exception as error:
                raise InstitutionClientError(f"Request to {url} failed.") from error

        raise InstitutionClientError(
            f"Request to {url} failed. Max attempts ({max_attempts}) reached."
        )

    def _get_retry_after_duration(
        self,
        response: requests.Response,
        attempt: int,
        initial_backoff: float,
        exponential_backoff: bool = False,
    ) -> float:
        return float(
            response.headers.get(
                "Retry-After",
                (
                    (initial_backoff * (2**(attempt - 1)))
                    if exponential_backoff
                    else initial_backoff
                ),
            )
        )

    def _get_endpoint_url(self, endpoint: Trading212ApiEndpoint) -> str:
        return urljoin(self._BASE_URL.rstrip("/") + "/", endpoint.value.lstrip("/"))
