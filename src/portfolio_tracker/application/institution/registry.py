from typing import Any, TypeVar

from portfolio_tracker.domain.institution import Credentials, Institution, InstitutionId

from portfolio_tracker.application.shared.exceptions import InstitutionNotFoundError

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

    def get_institution(self, institution_id: InstitutionId) -> Institution:
        return self._get(self._institutions, institution_id)

    def get_institution_id(self, institution_code: str) -> InstitutionId:
        return self._institution_id_cls(institution_code)

    def create_credentials(
        self, institution_id: InstitutionId, data: dict[str, Any]
    ) -> Credentials:
        return self._get(self._credentials_map, institution_id)(
            institution_id=institution_id,
            **data,
        )

    def create_client(
        self, institution_id: InstitutionId, credentials: Credentials
    ) -> InstitutionClient[Any]:
        credentials_cls = self._get(self._credentials_map, institution_id)

        if not isinstance(credentials, credentials_cls):
            raise TypeError(
                "Invalid credentials type. "
                f"Expected {credentials_cls.__name__}, got {type(credentials).__name__}."
            )

        return self._get(self._client_map, institution_id)(credentials)

    def create_parser(
        self, institution_id: InstitutionId, institution_account_id: str
    ) -> InstitutionReportParser:
        return self._get(self._parser_map, institution_id)(institution_account_id)

    def _get(
        self, registry: dict[InstitutionId, TItem], institution_id: InstitutionId
    ) -> TItem:
        try:
            return registry[institution_id]
        except KeyError as error:
            raise InstitutionNotFoundError(institution_id) from error
