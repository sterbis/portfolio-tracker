from dataclasses import asdict
from pprint import pformat

from portfolio_tracker.application.contracts.exceptions import (
    AppError,
    EntityNotFoundError,
)
from portfolio_tracker.domain.institution import Credentials, InstitutionId


class AssetAccountNotFoundError(EntityNotFoundError):
    def __init__(self, account_id: str) -> None:
        super().__init__(entity_name="Asset account", entity_id=account_id)


class AssetAccountAlreadyHasStatusError(AppError):
    _message_template = "Asset account with ID {account_id} is already {status}."


class AssetAccountAlreadyActivatedError(AssetAccountAlreadyHasStatusError):
    def __init__(self, account_id: str) -> None:
        super().__init__(account_id=account_id, status="activated")


class AssetAccountAlreadyDeactivatedError(AssetAccountAlreadyHasStatusError):
    def __init__(self, account_id: str) -> None:
        super().__init__(account_id=account_id, status="deactivated")


class InstitutionAccountNotFoundError(EntityNotFoundError):
    def __init__(self, account_id: str) -> None:
        super().__init__(entity_name="Institution account", entity_id=account_id)


class CredentialsNotFoundError(AppError):
    _message_template = "Credentials for institution account with ID {institution_account_id} not found."

    def __init__(self, institution_account_id: str) -> None:
        super().__init__(institution_account_id=institution_account_id)


class InvalidCredentialsError(AppError):
    _message_template = "Cannot connect to institution {institution_id} API with provided credentials:\n{credentials}."

    def __init__(self, institution_id: InstitutionId, credentials: Credentials) -> None:
        super().__init__(
            institution_id=institution_id,
            credentials=pformat(asdict(credentials), sort_dicts=False),
        )
