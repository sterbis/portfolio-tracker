from collections.abc import Iterable
from pprint import pformat
from typing import Any

from portfolio_tracker.domain.institution import Credentials, InstitutionId


class PortfolioTrackerError(Exception):
    _message_template = "An undefined error occurred."

    def __init__(self, **kwargs: Any) -> None:
        self.context = kwargs
        super().__init__(self.message)

    @property
    def message(self) -> str:
        return self._message_template.format(
            **{
                key: (
                    ", ".join(str(item) for item in value)
                    if isinstance(value, Iterable)
                    and not isinstance(value, (str, bytes))
                    else value
                )
                for key, value in self.context.items()
            }
        )


class ClientError(PortfolioTrackerError):
    def __init__(self, message: str) -> None:
        self._message = message
        super().__init__()

    @property
    def message(self) -> str:
        return self._message


class DataIntegrityError(PortfolioTrackerError): ...


class InvalidFilterError(PortfolioTrackerError):
    _message_template = "Cannot split OR filter tree combining persisted fields and in-memory computed fields."


class EntityNotFoundError(PortfolioTrackerError):
    _message_template = "{entity_name} with ID '{entity_id}' not found."
    _entity_name = "Unknow entity"

    def __init__(self, entity_id: str | set[str]) -> None:
        super().__init__(entity_name=self._entity_name, entity_id=entity_id)


class AssetAccountNotFoundError(EntityNotFoundError):
    _entity_name = "Asset account"

    def __init__(self, account_id: str | set[str]) -> None:
        super().__init__(entity_id=account_id)


class AssetAccountAlreadyHasStatusError(PortfolioTrackerError):
    _message_template = "Asset account with ID {account_id} is already {status}."
    _status = "unknow status"

    def __init__(self, account_id: str) -> None:
        super().__init__(account_id=account_id, status=self._status)


class AssetAccountAlreadyActivatedError(AssetAccountAlreadyHasStatusError):
    _status = "activated"


class AssetAccountAlreadyDeactivatedError(AssetAccountAlreadyHasStatusError):
    _status = "deactivated"


class InstitutionConnectionNotFoundError(EntityNotFoundError):
    _entity_name = "Institution connection"

    def __init__(self, connection_id: str | set[str]) -> None:
        super().__init__(entity_id=connection_id)


class CredentialsNotFoundError(EntityNotFoundError):
    _message_template = (
        "Credentials for institution connection with ID {entity_id} not found."
    )

    def __init__(self, institution_connection_id: str) -> None:
        super().__init__(entity_id=institution_connection_id)


class InvalidCredentialsError(PortfolioTrackerError):
    _message_template = "Cannot connect to institution {institution_id} API with provided credentials:\n{credentials}."

    def __init__(self, credentials: Credentials) -> None:
        super().__init__(
            institution_id=credentials.institution_id,
            credentials=pformat(credentials.parameters, sort_dicts=False),
        )


class InvalidCredentialParametersError(PortfolioTrackerError):
    _message_template = (
        "Invalid institution {institution_id} API credentials:\n"
        "Required parameters: {required_parameters}\n"
        "Missing parameters: {missing_parameters}\n"
        "Unknown parameters: {unknown_parameters}\n"
    )

    def __init__(
        self,
        institution_id: InstitutionId,
        required_parameters: tuple[str, ...],
        missing_parameters: list[str] | None = None,
        unknown_parameters: list[str] | None = None,
    ) -> None:
        super().__init__(
            institution_id=institution_id,
            required_parameters=required_parameters,
            missing_parameters=missing_parameters or [],
            unknown_parameters=unknown_parameters or [],
        )


class InvalidUsernameOrPasswordError(PortfolioTrackerError):
    _message_template = "Invalid username or password."


class UserNotLoggedInError(PortfolioTrackerError):
    _message_template = "No user is currently logged in."


class UserAlreadyLoggedOutError(PortfolioTrackerError):
    _message_template = "User already logged out."


class FxClientError(ClientError): ...


class FxDataIntegrityError(DataIntegrityError):
    _message_template = "Fx Data Integrity Error: {detail}"

    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail)


class InstitutionClientError(ClientError): ...


class InstitutionReportNotFoundError(PortfolioTrackerError): ...


class InstitutionReportParserError(PortfolioTrackerError): ...


class InstitutionNotFoundError(EntityNotFoundError):
    _entity_name = "Institution"

    def __init__(self, institution_id: InstitutionId | set[str]) -> None:
        super().__init__(entity_id=institution_id)


class MarketDataClientError(ClientError): ...


class MarketDataIntegrityError(DataIntegrityError):
    _message_template = "Market Data Integrity Error: {detail}"

    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail)


class TransactionAlreadyExistsError(PortfolioTrackerError):
    _message_template = "Transaction with ID {transaction_id} already exists."


class TransactionNotFoundError(EntityNotFoundError):
    _entity_name = "Transaction"

    def __init__(self, transaction_id: str | set[str]) -> None:
        super().__init__(entity_id=transaction_id)


class UsernameAlreadyExistsError(PortfolioTrackerError):
    _message_template = "User with '{username}' username already exists."

    def __init__(self, username: str) -> None:
        super().__init__(username=username)
