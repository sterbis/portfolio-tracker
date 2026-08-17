from typing import Any

from portfolio_tracker.application.institution import (
    InstitutionClient,
    InstitutionRegistry,
    InstitutionReportParser,
)
from portfolio_tracker.domain.institution import Credentials, Institution, InstitutionId

from .ibkr import IbkrCredentials
from .trading_212 import Trading212Client, Trading212Credentials, Trading212ReportParser


class InstitutionCode(InstitutionId):
    TRADING_212 = "T212"
    INTERACTIVE_BROKERS = "IBKR"


_INSTITUTIONS: dict[InstitutionId, Institution] = {
    InstitutionCode.TRADING_212: Institution(
        id=InstitutionCode.TRADING_212,
        name="Trading 212",
        log_in_url="https://www.trading212.com",
    ),
    InstitutionCode.INTERACTIVE_BROKERS: Institution(
        id=InstitutionCode.INTERACTIVE_BROKERS,
        name="Interactive Brokers",
        log_in_url="https://www.interactivebrokers.com",
    ),
}

_CREDENTIALS: dict[InstitutionId, type[Credentials]] = {
    InstitutionCode.TRADING_212: Trading212Credentials,
    InstitutionCode.INTERACTIVE_BROKERS: IbkrCredentials,
}

_CLIENTS: dict[InstitutionId, type[InstitutionClient[Any]]] = {
    InstitutionCode.TRADING_212: Trading212Client,
}

_PARSERS: dict[InstitutionId, type[InstitutionReportParser]] = {
    InstitutionCode.TRADING_212: Trading212ReportParser,
}


def create_institution_registry() -> InstitutionRegistry:
    return InstitutionRegistry(
        institution_id_cls=InstitutionCode,
        institution_map=_INSTITUTIONS,
        credentials_map=_CREDENTIALS,
        client_map=_CLIENTS,
        parser_map=_PARSERS,
    )
