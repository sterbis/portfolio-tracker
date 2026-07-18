from dataclasses import dataclass
from typing import Any, TypeVar

from portfolio_tracker.application.institution import (
    InstitutionClient,
    InstitutionNotFoundError,
    InstitutionRegistry,
    InstitutionReportParser,
)
from portfolio_tracker.domain.institution import Credentials, Institution

from .trading_212 import Trading212Client, Trading212Credentials, Trading212ReportParser


TItem = TypeVar("TItem")


@dataclass(frozen=True)
class IbkrCredentials(Credentials):
    flex_web_service_token: str
    flex_query_ids: list[str]


_INSTITUTIONS: dict[str, Institution] = {
    "T212": Institution(
        id="T212",
        name="Trading 212",
        log_in_url="https://www.trading212.com",
        credentials_cls=Trading212Credentials,
    ),
    "IBKR": Institution(
        id="IBKR",
        name="Interactive Brokers",
        log_in_url="https://www.interactivebrokers.com",
        credentials_cls=IbkrCredentials,
    ),
}

_CLIENTS: dict[str, type[InstitutionClient[Any]]] = {
    "T212": Trading212Client,
}

_PARSERS: dict[str, type[InstitutionReportParser]] = {
    "T212": Trading212ReportParser,
}


def create_registry() -> InstitutionRegistry:
    return InstitutionRegistry(_INSTITUTIONS)


def create_client(
    institution_id: str, credentials: Credentials
) -> InstitutionClient[Any]:
    institution = _get(_INSTITUTIONS, institution_id)

    if not isinstance(credentials, institution.credentials_cls):
        raise TypeError(
            f"Invalid {institution.name} credentials type. "
            f"Expected {institution.credentials_cls.__name__}, got {type(credentials).__name__}."
        )

    return _get(_CLIENTS, institution_id)(credentials)


def create_parser(
    institution_id: str, institution_account_id: str
) -> InstitutionReportParser:
    return _get(_PARSERS, institution_id)(institution_account_id)


def _get(registry: dict[str, TItem], institution_id: str) -> TItem:
    try:
        return registry[institution_id]
    except KeyError as error:
        raise InstitutionNotFoundError(institution_id) from error
