from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import (
    StorageConnectionFactory,
    StorageReadConnectionFactory,
)
from portfolio_tracker.application.security import Encryptor

from .database import initialize_database
from .mappers import register_mappers
from .registry import SCHEMA_REGISTRY
from .unit_of_work import SqliteStorageConnectionFactory, SqliteStorageReadConnectionFactory


def initialize(
    uri: str,
    institution_registry: InstitutionRegistry,
    encryptor: Encryptor,
) -> tuple[StorageReadConnectionFactory, StorageConnectionFactory]:
    initialize_database(uri)
    register_mappers()

    read_connection_factory = SqliteStorageReadConnectionFactory(
        uri=uri,
        schema_registry=SCHEMA_REGISTRY,
        institution_registry=institution_registry,
        encryptor=encryptor,
    )
    connection_factory = SqliteStorageConnectionFactory(
        uri=uri,
        schema_registry=SCHEMA_REGISTRY,
        institution_registry=institution_registry,
        encryptor=encryptor,
    )

    return read_connection_factory, connection_factory
