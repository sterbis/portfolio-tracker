import typing
from typing import Any, Callable, TypeVar

from portfolio_tracker.application.shared.errors import (
    InstitutionNotFoundError,
    InvalidCredentialParametersError,
)
from portfolio_tracker.domain.institution import Credentials, Institution, InstitutionId

from .client import InstitutionClient
from .report_parser import InstitutionReportParser

TItem = TypeVar("TItem")


class InstitutionRegistry:
    def __init__(
        self,
        institution_id_cls: type[InstitutionId],
        institution_map: dict[InstitutionId, Institution],
        credentials_map: dict[InstitutionId, type[Credentials]],
        client_map: dict[InstitutionId, type[InstitutionClient[Any]]],
        parser_map: dict[InstitutionId, type[InstitutionReportParser]],
    ) -> None:
        self._institution_id_cls = institution_id_cls
        self._institutions = institution_map
        self._credentials_map = credentials_map
        self._client_map = client_map
        self._parser_map = parser_map

    def get_institution_id(self, institution_id_string: str) -> InstitutionId:
        return self._institution_id_cls(institution_id_string)

    def get_institution(self, institution_id: InstitutionId) -> Institution:
        return self._get(self._institutions, institution_id)

    def get_credentials_cls(self, institution_id: InstitutionId) -> type[Credentials]:
        return self._get(self._credentials_map, institution_id)

    def create_credentials(
        self,
        institution_id: InstitutionId,
        institution_account_id: str,
        parameters: dict[str, Any],
    ) -> Credentials:
        return self.get_credentials_cls(institution_id)(
            institution_id=institution_id,
            institution_account_id=institution_account_id,
            **parameters,
        )

    def create_client(self, credentials: Credentials) -> InstitutionClient[Any]:
        credentials_cls = self._get(self._credentials_map, credentials.institution_id)

        if not isinstance(credentials, credentials_cls):
            raise TypeError(
                "Invalid credentials type. "
                f"Expected {credentials_cls.__name__}, got {type(credentials).__name__}."
            )

        return self._get(self._client_map, credentials.institution_id)(credentials)

    def create_report_parser(
        self, institution_id: InstitutionId, institution_account_id: str
    ) -> InstitutionReportParser:
        return self._get(self._parser_map, institution_id)(institution_account_id)

    def parse_credential_parameters(
        self, institution_id: InstitutionId, parameters: dict[str, str]
    ) -> dict[str, Any]:
        converters: dict[Any, Callable[[str], Any]] = {
            str: str,
            list[str]: lambda value: [
                item.strip() for item in value.split(",") if item.strip()
            ],
        }

        credentials_cls = self.get_credentials_cls(institution_id)
        required_parameters = credentials_cls.parameter_names()

        missing_parameters = [
            name for name in required_parameters if name not in parameters
        ]
        unknown_parameters = [
            name for name in parameters if name not in required_parameters
        ]
        if missing_parameters or unknown_parameters:
            raise InvalidCredentialParametersError(
                institution_id,
                required_parameters,
                missing_parameters,
                unknown_parameters,
            )

        return {
            name: converters[type_hint](parameters[name])
            for name, type_hint in typing.get_type_hints(credentials_cls).items()
            if name in required_parameters
        }

    def get_credential_parameter_names(
        self, institution_id: InstitutionId
    ) -> tuple[str, ...]:
        return self._get(self._credentials_map, institution_id).parameter_names()

    def _get(
        self, registry: dict[InstitutionId, TItem], institution_id: InstitutionId
    ) -> TItem:
        try:
            return registry[institution_id]
        except KeyError as error:
            raise InstitutionNotFoundError(institution_id) from error
