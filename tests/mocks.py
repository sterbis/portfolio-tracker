from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from portfolio_tracker.application.security import Encryptor
from portfolio_tracker.domain.institution import Credentials, InstitutionId
from portfolio_tracker.domain.shared import DeterministicIdEntity


class MockEncryptor(Encryptor):
    def encrypt(self, plain_text: str) -> str:
        return f"encrypted_{plain_text}"

    def decrypt(self, encrypted_text: str) -> str:
        return encrypted_text.replace("encrypted_", "")


class MockInstitutionCode(InstitutionId):
    TRADING_321 = "T321"
    HYPERACTIVE_BROKERS = "HBKR"


@dataclass(frozen=True)
class Trading321Credentials(Credentials):
    account_id: str
    api_key: str
    api_secret: str

    @classmethod
    def parameter_names(cls) -> tuple[str, ...]:
        return ("account_id", "api_key", "api_secret")

    @classmethod
    def secret_parameter_names(cls) -> tuple[str, ...]:
        return ("api_secret",)


@dataclass(frozen=True)
class HyperactiveBrokersCredentials(Credentials):
    web_service_token: str
    query_ids: list[str]

    @classmethod
    def parameter_names(cls) -> tuple[str, ...]:
        return ("web_service_token", "query_ids")

    @classmethod
    def secret_parameter_names(cls) -> tuple[str, ...]:
        return ("web_service_token",)


@dataclass(frozen=True, kw_only=True)
class MockDeterministicIdEntity(DeterministicIdEntity):
    created_at: datetime
    name: str
    value: Decimal
    note: str

    @property
    def _id_prefix(self) -> str:
        return "mock"

    @property
    def _identity(self) -> str:
        return f"{self.created_at.isoformat()}|{self.name}|{self.value.normalize()}"

    def _validate(self) -> None:
        if self.value > 100:
            raise ValueError("Value cannot be greater than 100.")
