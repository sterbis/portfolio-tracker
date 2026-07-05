from dataclasses import dataclass

from portfolio_tracker.domain.institution import Credentials, Institution


@dataclass(frozen=True)
class Trading212Credentials(Credentials):
    account_id: str
    api_key: str
    api_secret: str


@dataclass(frozen=True)
class IbkrCredentials(Credentials):
    flex_web_service_token: str
    flex_query_ids: list[str]


SUPPORTED_INSTITUTIONS: dict[str, Institution] = {
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
