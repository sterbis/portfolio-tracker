# pylint: disable=redefined-outer-name
# pylint: disable=protected-access

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
import requests

from portfolio_tracker.application.institution import InstitutionClientError
from portfolio_tracker.infrastructure.institution.trading_212.client import (
    Trading212ApiEndpoints,
    Trading212Client,
    Trading212Credentials,
)


@pytest.fixture
def trading_212_client() -> Trading212Client:
    return Trading212Client(
        credentials=Trading212Credentials(
            api_key="api_key",
            api_secret="api_secret",
        )
    )


@pytest.mark.asyncio
async def test_request_returns_successful_response_immediately(
    monkeypatch: pytest.MonkeyPatch, trading_212_client: Trading212Client
) -> None:
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.raise_for_status = Mock()

    request = Mock(return_value=response)
    monkeypatch.setattr(requests, "request", request)

    result = await trading_212_client._request(
        Trading212ApiEndpoints.ACCOUNT_SUMMARY, auth=("api_key", "api_secret")
    )

    assert result is response
    request.assert_called_once_with(
        method="GET",
        url=Trading212ApiEndpoints.ACCOUNT_SUMMARY.build_url(
            trading_212_client._BASE_URL
        ),
        params=None,
        json=None,
        data=None,
        headers=None,
        auth=("api_key", "api_secret"),
        timeout=5.0,
    )
    response.raise_for_status.assert_called_once()


@pytest.mark.asyncio
async def test_request_retries_on_429_and_returns_when_successful(
    monkeypatch: pytest.MonkeyPatch, trading_212_client: Trading212Client
) -> None:
    first_response = Mock(spec=requests.Response)
    first_response.headers = {}
    first_response.status_code = 429
    first_response.reason = "Too many requests"
    first_response.raise_for_status = Mock()
    first_response.raise_for_status.side_effect = requests.HTTPError(
        "429 Too many requests", response=first_response
    )

    second_response = Mock(spec=requests.Response)
    second_response.status_code = 200
    second_response.raise_for_status = Mock()

    request = Mock(side_effect=[first_response, second_response])
    monkeypatch.setattr(requests, "request", request)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    result = await trading_212_client._request(Trading212ApiEndpoints.ACCOUNT_SUMMARY)

    assert result is second_response
    assert request.call_count == 2
    second_response.raise_for_status.assert_called_once()


@pytest.mark.asyncio
async def test_request_raises_institution_client_error_on_non_429_error(
    monkeypatch: pytest.MonkeyPatch, trading_212_client: Trading212Client
) -> None:
    response = Mock(spec=requests.Response)
    response.status_code = 500
    response.reason = "Internal Server Error"
    response.raise_for_status = Mock(
        side_effect=requests.HTTPError("500 Internal Server Error", response=response)
    )

    request = Mock(return_value=response)
    monkeypatch.setattr(requests, "request", request)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    with pytest.raises(
        InstitutionClientError,
        match="Request to .+ failed after 3 attempts. Status: 500, reason: Internal Server Error",
    ):
        await trading_212_client._request(Trading212ApiEndpoints.ACCOUNT_SUMMARY)
