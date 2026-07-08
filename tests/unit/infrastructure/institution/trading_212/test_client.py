# pylint: disable=redefined-outer-name
# pylint: disable=protected-access

from unittest.mock import Mock

import pytest
import requests

from portfolio_tracker.application.supported_institutions import Trading212Credentials
from portfolio_tracker.application.institution import InstitutionClientError
from portfolio_tracker.infrastructure.institution.trading_212.client import (
    Trading212Client,
)


@pytest.fixture
def trading_212_client() -> Trading212Client:
    return Trading212Client(
        credentials=Trading212Credentials(
            api_key="api_key",
            api_secret="api_secret",
        )
    )


def test_request_returns_successful_response_immediately(
    monkeypatch: pytest.MonkeyPatch, trading_212_client: Trading212Client
) -> None:
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.raise_for_status = Mock()

    request = Mock(return_value=response)
    monkeypatch.setattr(requests, "request", request)

    result = trading_212_client._request(method="GET", url="https://example.com")

    assert result is response
    request.assert_called_once_with(
        "GET",
        "https://example.com",
        params=None,
        json=None,
        data=None,
        headers=None,
        auth=("api_key", "api_secret"),
        timeout=5.0,
    )
    response.raise_for_status.assert_called_once()


def test_request_retries_on_429_and_returns_when_successful(
    monkeypatch: pytest.MonkeyPatch, trading_212_client: Trading212Client
) -> None:
    first_response = Mock(spec=requests.Response)
    first_response.status_code = 429
    first_response.raise_for_status = Mock()

    second_response = Mock(spec=requests.Response)
    second_response.status_code = 200
    second_response.raise_for_status = Mock()

    request = Mock(side_effect=[first_response, second_response])
    monkeypatch.setattr(requests, "request", request)
    monkeypatch.setattr("time.sleep", lambda _: None)

    result = trading_212_client._request(method="GET", url="https://example.com")

    assert result is second_response
    assert request.call_count == 2
    second_response.raise_for_status.assert_called_once()


def test_request_raises_institution_client_error_on_non_429_error(
    monkeypatch: pytest.MonkeyPatch, trading_212_client: Trading212Client
) -> None:
    response = Mock(spec=requests.Response)
    response.status_code = 500
    response.reason = "Internal Server Error"
    response.raise_for_status = Mock(side_effect=requests.HTTPError("server error"))

    request = Mock(return_value=response)
    monkeypatch.setattr(requests, "request", request)

    with pytest.raises(
        InstitutionClientError,
        match="Request to https://example.com failed: 500 Internal Server Error.",
    ):
        trading_212_client._request(method="GET", url="https://example.com")
