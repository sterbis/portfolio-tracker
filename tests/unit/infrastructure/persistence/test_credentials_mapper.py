from typing import Any

import pytest

from portfolio_tracker.domain.institution import InstitutionRegistry
from portfolio_tracker.infrastructure.persistence.credentials_serializer import (
    deserialize_credentials,
    serialize_credentials,
)


@pytest.mark.parametrize(
    "instituion_id, credentials_parameters, expected_serialized_credetials",
    [
        (
            "inst_001",
            {
                "api_key": "key_123",
                "api_secret": "secret_abc",
            },
            '{"api_key": "key_123", "api_secret": "secret_abc"}',
        ),
        (
            "inst_002",
            {
                "web_service_token": "token_#@$",
                "query_ids": ["q1", "q2"],
            },
            '{"web_service_token": "token_#@$", "query_ids": ["q1", "q2"]}',
        ),
    ],
)
def test_serialize_credentials_round_trip(
    instituion_id: str,
    credentials_parameters: dict[str, Any],
    expected_serialized_credetials: str,
    sample_institution_registry: InstitutionRegistry,
) -> None:
    institution = sample_institution_registry.get(instituion_id)
    credentials = institution.credentials_cls(**credentials_parameters)

    serialized_credetials = serialize_credentials(credentials)
    assert serialized_credetials == expected_serialized_credetials

    deserialized_credentials = deserialize_credentials(
        institution, serialized_credetials
    )
    assert deserialized_credentials == credentials
