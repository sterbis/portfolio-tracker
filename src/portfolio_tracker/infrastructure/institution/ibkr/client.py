from dataclasses import dataclass

from portfolio_tracker.domain.institution import Credentials


@dataclass(frozen=True)
class IbkrCredentials(Credentials):
    flex_web_service_token: str
    flex_query_ids: list[str]

    @classmethod
    def parameter_names(cls) -> tuple[str, ...]:
        return ("flex_web_service_token", "flex_query_ids")

    @classmethod
    def secret_parameter_names(cls) -> tuple[str, ...]:
        return ("flex_web_service_token", )
