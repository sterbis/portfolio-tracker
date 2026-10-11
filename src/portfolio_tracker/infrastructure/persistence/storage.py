from importlib import import_module

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import (
    StorageConnectionFactory,
    StorageReadConnectionFactory,
)
from portfolio_tracker.application.security import Encryptor
from portfolio_tracker.infrastructure.configuration import StorageType

_STORAGE_MODULE_REGISTRY: dict[StorageType, str] = {
    StorageType.SQLITE: ".sqlite",
}


def initialize_storage(
    type_: StorageType,
    uri: str,
    institution_registry: InstitutionRegistry,
    encryptor: Encryptor,
) -> tuple[StorageReadConnectionFactory, StorageConnectionFactory]:
    module_path = _STORAGE_MODULE_REGISTRY.get(type_)
    if not module_path:
        raise ValueError(f"Unexpected storage type: '{type_}'.")

    module = import_module(module_path, package=__package__)

    storage_connections: tuple[
        StorageReadConnectionFactory, StorageConnectionFactory
    ] = module.initialize(
        uri=uri,
        institution_registry=institution_registry,
        encryptor=encryptor,
    )
    return storage_connections
