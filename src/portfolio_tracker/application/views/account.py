from dataclasses import dataclass

from portfolio_tracker.domain.account import AssetAccount

from .institution import InstitutionConnectionView


@dataclass(frozen=True, kw_only=True)
class AssetAccountView:
    id: str
    institution_connection: InstitutionConnectionView
    external_id: str
    name: str
    is_active: bool

    @classmethod
    def from_domain(
        cls,
        account: AssetAccount,
        institution_connection_view: InstitutionConnectionView,
    ) -> AssetAccountView:
        return cls(
            id=account.id,
            institution_connection=institution_connection_view,
            external_id=account.external_id,
            name=account.name,
            is_active=account.is_active,
        )
