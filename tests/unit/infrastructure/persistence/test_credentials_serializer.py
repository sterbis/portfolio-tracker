import pytest

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.domain.institution import Credentials
from portfolio_tracker.infrastructure.persistence.credentials_serializer import (
    deserialize_credentials,
    serialize_credentials,
)
from tests.mocks import (
    HyperactiveBrokersCredentials,
    MockInstitutionCode,
    Trading321Credentials,
)


@pytest.mark.parametrize(
    "instituion_id, credentials, expected_serialized_credetials",
    [
        (
            MockInstitutionCode.TRADING_321,
            Trading321Credentials(
                api_key="key_123",
                api_secret="secret_abc",
            ),
            '{"api_key": "key_123", "api_secret": "secret_abc"}',
        ),
        (
            MockInstitutionCode.HYPERACTIVE_BROKERS,
            HyperactiveBrokersCredentials(
                web_service_token="token_#@$",
                query_ids=["q1", "q2"],
            ),
            '{"web_service_token": "token_#@$", "query_ids": ["q1", "q2"]}',
        ),
    ],
)
def test_serialize_credentials_round_trip(
    instituion_id: MockInstitutionCode,
    credentials: Credentials,
    expected_serialized_credetials: str,
    sample_institution_registry: InstitutionRegistry,
) -> None:
    serialized_credetials = serialize_credentials(credentials)
    assert serialized_credetials == expected_serialized_credetials

    institution = sample_institution_registry.get(instituion_id)

    deserialized_credentials = deserialize_credentials(
        institution, serialized_credetials
    )
    assert deserialized_credentials == credentials
