# pylint: disable=redefined-outer-name
# pylint: disable=protected-access

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest

from tests.mocks import MockDeterministicIdEntity


@pytest.fixture(scope="session")
def mock_entity() -> MockDeterministicIdEntity:
    return MockDeterministicIdEntity(
        created_at=datetime(2026, 1, 1, 12, 30, 0),
        name="Mock Entity",
        value=Decimal("42.000"),
        note="this can change",
    )


def test_entity_id_is_deterministic(mock_entity: MockDeterministicIdEntity) -> None:
    assert mock_entity.id == "mock_3eadbb737aac4d47"


def test_entity_identity(mock_entity: MockDeterministicIdEntity) -> None:
    assert mock_entity._identity == "2026-01-01T12:30:00|Mock Entity|42"


def test_valid_provided_id_is_accepted(
    mock_entity: MockDeterministicIdEntity,
) -> None:
    MockDeterministicIdEntity(
        provided_id="mock_3eadbb737aac4d47",
        created_at=mock_entity.created_at,
        name=mock_entity.name,
        value=mock_entity.value,
        note=mock_entity.note,
    )


def test_invalid_provided_id_raises_error(
    mock_entity: MockDeterministicIdEntity,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Provided MockDeterministicIdEntity id 'mock_0123456abcdefg' "
            "does not match computed id 'mock_3eadbb737aac4d47'."
        ),
    ):
        MockDeterministicIdEntity(
            provided_id="mock_0123456abcdefg",
            created_at=mock_entity.created_at,
            name=mock_entity.name,
            value=mock_entity.value,
            note=mock_entity.note,
        )


def test_replacing_identity_attribute_changes_id(
    mock_entity: MockDeterministicIdEntity,
) -> None:
    updated_mock_entity = replace(mock_entity, value=Decimal("3"))
    assert updated_mock_entity.id != mock_entity.id
    assert updated_mock_entity._identity != mock_entity._identity


def test_replacing_non_identity_attribute_keeps_id(
    mock_entity: MockDeterministicIdEntity,
) -> None:
    updated_mock_entity = replace(mock_entity, note="changed")
    assert updated_mock_entity.id == mock_entity.id
    assert updated_mock_entity._identity == mock_entity._identity


def test_validation_run_after_instantiation(
    mock_entity: MockDeterministicIdEntity,
) -> None:
    with pytest.raises(ValueError, match="Value cannot be greater than 100."):
        replace(mock_entity, value=Decimal("101"))
