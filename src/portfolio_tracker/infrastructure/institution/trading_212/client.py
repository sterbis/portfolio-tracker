import csv
from datetime import datetime, timezone
from enum import StrEnum
from io import StringIO
import time
from typing import Any, Literal
from urllib.parse import urljoin

import requests

from portfolio_tracker.application.institution import InstitutionClient, InstitutionClientError
from portfolio_tracker.application.supported_institutions import Trading212Credentials


class Trading212ApiEndpoint(StrEnum):
    ACCOUNT_SUMMARY = "equity/account/summary"
    ORDERS = "equity/history/orders"
    PENDING_ORDERS = "equity/orders"
    POSITIONS = "equity/positions"
    REPORTS = "equity/history/exports"
    TRANSACTIONS = "equity/history/transactions"


class Trading212Client(InstitutionClient[Trading212Credentials]):
    _BASE_URL = "https://live.trading212.com/api/v0/"
    _MAX_REPORT_CHUNK_DAYS = 365
    _TIMEZONE = timezone.utc

    def __init__(self, credentials: Trading212Credentials) -> None:
        super().__init__(credentials)

    def _fetch_report_chunk(self, start: datetime, end: datetime) -> str:
        report_id = self._generate_report(start, end)
        report = self._fetch_report_by_id(report_id)
        if not report:
            raise InstitutionClientError(
                f"No available data for time range: {start} - {end}."
            )

        return report

    def _merge_report_chunks(self, chunks: list[str]) -> str:
        records: list[dict[str, Any]] = []
        report_columns: list[str] = []

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            reader = csv.DictReader(StringIO(chunk, newline=None))
            if reader.fieldnames is None:
                raise InstitutionClientError(f"Report does not contain header row.\n{chunk}")

            for column in reader.fieldnames:
                if column not in report_columns:
                    report_columns.append(column)

            records.extend(list(reader))

        report = StringIO(newline=None)

        writer = csv.DictWriter(report, fieldnames=report_columns, restval="")
        writer.writeheader()
        writer.writerows(records)

        return report.getvalue()

    def _generate_report(
        self,
        start: datetime,
        end: datetime,
        dividends: bool = True,
        interest: bool = True,
        orders: bool = True,
        transactions: bool = True,
    ) -> int:
        response = self._request(
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

    def _fetch_report_by_id(self, report_id: int) -> str:
        report_metadata = self._wait_for_report_generation(report_id)
        response = self._request(
            method="GET",
            url=report_metadata["downloadLink"],
        )
        return response.text

    def _wait_for_report_generation(
        self,
        report_id: int,
        timeout: float = 300,
        initial_delay: float = 30,
        poll_interval: float = 60,
    ) -> dict[str, Any]:
        time.sleep(initial_delay)

        deadline = time.time() + timeout

        while True:
            try:
                metadata = self._fetch_report_metadata(report_id)
            except InstitutionClientError:
                metadata = {}

            if metadata.get("status") == "Finished":
                return metadata

            if time.time() + poll_interval > deadline:
                raise InstitutionClientError(
                    f"Report {report_id} generation not finished within timeout: {timeout} seconds."
                )

            time.sleep(poll_interval)

    def _fetch_report_metadata(self, report_id: int) -> dict[str, Any]:
        reports_metadata: list[dict[str, Any]] = self._request(
            method="GET",
            endpoint=Trading212ApiEndpoint.REPORTS,
            max_retries=0,
            exponential_backoff=False,
        ).json()

        for metadata in reports_metadata:
            if int(metadata["reportId"]) == report_id:
                return metadata

        raise InstitutionClientError(f"Report with id {report_id} not found.")

    def _request(
        self,
        method: Literal["GET", "POST"],
        url: str | None = None,
        endpoint: Trading212ApiEndpoint | None = None,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 5.0,
        max_retries: int = 2,
        base_sleep_time: float = 5.0,
        exponential_backoff: bool = True,
    ) -> requests.Response:
        if not url and not endpoint:
            raise ValueError("No url or endpoint provided.")

        url = url or self._BASE_URL
        if endpoint:
            url = urljoin(url.rstrip("/") + "/", endpoint.value.lstrip("/"))

        retries = 0

        while True:
            try:
                response = requests.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                    headers=headers,
                    auth=(self._credentials.api_key, self._credentials.api_secret),
                    timeout=timeout,
                )
            except requests.RequestException as error:
                raise InstitutionClientError(
                    f"Request to {url} failed."
                ) from error

            if response.status_code == 429 and retries < max_retries:
                sleep_time = (
                    base_sleep_time * (2 ** retries)
                    if exponential_backoff
                    else base_sleep_time
                )
                time.sleep(sleep_time)
                retries += 1
                continue

            try:
                response.raise_for_status()
            except requests.RequestException as error:
                raise InstitutionClientError(
                    f"Request to {url} failed: {response.status_code} {response.reason}."
                ) from error

            return response
