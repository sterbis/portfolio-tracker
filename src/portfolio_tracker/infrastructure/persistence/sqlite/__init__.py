from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import (
    StorageConnection,
    StorageReadConnection,
)
from portfolio_tracker.application.security import Encryptor

from .database import initialize_database
from .mappers import register_mappers
from .registry import SCHEMA_REGISTRY
from .unit_of_work import SqliteStorageConnection


def initialize(
    uri: str,
    institution_registry: InstitutionRegistry,
    encryptor: Encryptor,
) -> tuple[StorageReadConnection, StorageConnection]:
    initialize_database(uri)
    register_mappers()

    read_connection = SqliteStorageConnection(
        uri=uri,
        schema_registry=SCHEMA_REGISTRY,
        institution_registry=institution_registry,
        encryptor=encryptor,
        read_only=True,
    )
    connection = SqliteStorageConnection(
        uri=uri,
        schema_registry=SCHEMA_REGISTRY,
        institution_registry=institution_registry,
        encryptor=encryptor,
    )

    return read_connection, connection
