import pytest

from tests.mocks import MockEncryptor


@pytest.fixture(scope="session")
def mock_encryptor() -> MockEncryptor:
    return MockEncryptor("secret_key")
