from dataclasses import dataclass

from portfolio_tracker.application.encryption import Encryptor
from portfolio_tracker.domain.institution import Credentials, InstitutionId


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
    api_key: str
    api_secret: str


@dataclass(frozen=True)
class HyperactiveBrokersCredentials(Credentials):
    web_service_token: str
    query_ids: list[str]
