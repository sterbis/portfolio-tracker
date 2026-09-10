from collections.abc import Sequence
from pprint import pformat
from typing import Any

from portfolio_tracker.domain.institution import Credentials, InstitutionId


class PortfolioTrackerError(Exception):
    _message_template = "{message}"

    def __init__(self, **kwargs: Any) -> None:
        self.context = kwargs or {"message": "An undefined error occurred."}
        super().__init__(self.message)

    @property
    def message(self) -> str:
        return self._message_template.format(
            **{
                key: ", ".join(value) if isinstance(value, Sequence) else str(value)
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


class ModelNotFoundError(PortfolioTrackerError):
    _message_template = "{model_name} with ID {model_id} not found."

    def __init__(self, model_name: str, model_id: str | set[str]) -> None:
        super().__init__(model_name=model_name, model_id=model_id)


class AssetAccountNotFoundError(ModelNotFoundError):
    def __init__(self, account_id: str | set[str]) -> None:
        super().__init__(model_name="Asset account", model_id=account_id)


class AssetAccountAlreadyHasStatusError(PortfolioTrackerError):
    _message_template = "Asset account with ID {account_id} is already {status}."
    _status = "unknow status"

    def __init__(self, account_id: str) -> None:
        super().__init__(account_id=account_id, status=self._status)


class AssetAccountAlreadyActivatedError(AssetAccountAlreadyHasStatusError):
    _status = "activated"


class AssetAccountAlreadyDeactivatedError(AssetAccountAlreadyHasStatusError):
    _status = "deactivated"


class InstitutionAccountNotFoundError(ModelNotFoundError):
    def __init__(self, account_id: str | set[str]) -> None:
        super().__init__(model_name="Institution account", model_id=account_id)


class CredentialsNotFoundError(PortfolioTrackerError):
    _message_template = "Credentials for institution account with ID {institution_account_id} not found."

    def __init__(self, institution_account_id: str) -> None:
        super().__init__(institution_account_id=institution_account_id)


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


class InstitutionNotFoundError(ModelNotFoundError):
    def __init__(self, institution_id: InstitutionId | set[str]) -> None:
        super().__init__(model_name="Institution", model_id=institution_id)


class MarketDataClientError(ClientError): ...


class MarketDataIntegrityError(DataIntegrityError):
    _message_template = "Market Data Integrity Error: {detail}"

    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail)


class TransactionAlreadyExistsError(PortfolioTrackerError):
    _message_template = "Transaction with ID {transaction_id} already exists."


class TransactionNotFoundError(ModelNotFoundError):
    def __init__(self, transaction_id: str | set[str]) -> None:
        super().__init__(model_name="Transaction", model_id=transaction_id)


class UsernameAlreadyExistsError(PortfolioTrackerError):
    _message_template = "User with '{username}' username already exists."

    def __init__(self, username: str) -> None:
        super().__init__(username=username)
