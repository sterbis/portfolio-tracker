# pylint: disable=redefined-outer-name

import pytest

from portfolio_tracker.infrastructure.persistence.sqlite import (
    register_mappers,
)


@pytest.fixture(scope="session", autouse=True)
def register_sqlite_mappers() -> None:
    register_mappers()


@pytest.fixture(scope="session")
def schema_path() -> str:
    return r"src\portfolio_tracker\infrastructure\persistence\sqlite\schema.sql"
