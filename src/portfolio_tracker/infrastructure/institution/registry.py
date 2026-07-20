from dataclasses import dataclass
from typing import Any, TypeVar

from portfolio_tracker.application.institution import (
    InstitutionClient,
    InstitutionNotFoundError,
    InstitutionRegistry,
    InstitutionReportParser,
)
from portfolio_tracker.domain.institution import Credentials, Institution, InstitutionId

from .trading_212 import Trading212Client, Trading212Credentials, Trading212ReportParser

TItem = TypeVar("TItem")


class InstitutionCode(InstitutionId):
    TRADING_212 = "T212"
    INTERACTIVE_BROKERS = "IBKR"


@dataclass(frozen=True)
class IbkrCredentials(Credentials):
    flex_web_service_token: str
    flex_query_ids: list[str]


_INSTITUTIONS: dict[InstitutionId, Institution] = {
    InstitutionCode.TRADING_212: Institution(
        id=InstitutionCode.TRADING_212,
        name="Trading 212",
        log_in_url="https://www.trading212.com",
        credentials_cls=Trading212Credentials,
    ),
    InstitutionCode.INTERACTIVE_BROKERS: Institution(
        id=InstitutionCode.INTERACTIVE_BROKERS,
        name="Interactive Brokers",
        log_in_url="https://www.interactivebrokers.com",
        credentials_cls=IbkrCredentials,
    ),
}

_CLIENTS: dict[InstitutionId, type[InstitutionClient[Any]]] = {
    InstitutionCode.TRADING_212: Trading212Client,
}

_PARSERS: dict[InstitutionId, type[InstitutionReportParser]] = {
    InstitutionCode.TRADING_212: Trading212ReportParser,
}


def create_registry() -> InstitutionRegistry:
    return InstitutionRegistry(_INSTITUTIONS, InstitutionCode)


def create_client(
    institution_id: InstitutionId, credentials: Credentials
) -> InstitutionClient[Any]:
    institution = _get(_INSTITUTIONS, institution_id)

    if not isinstance(credentials, institution.credentials_cls):
        raise TypeError(
            f"Invalid {institution.name} credentials type. "
            f"Expected {institution.credentials_cls.__name__}, got {type(credentials).__name__}."
        )

    return _get(_CLIENTS, institution_id)(credentials)


def create_parser(
    institution_id: InstitutionId, institution_account_id: str
) -> InstitutionReportParser:
    return _get(_PARSERS, institution_id)(institution_account_id)


def _get(registry: dict[InstitutionId, TItem], institution_id: InstitutionId) -> TItem:
    try:
        return registry[institution_id]
    except KeyError as error:
        raise InstitutionNotFoundError(institution_id) from error
