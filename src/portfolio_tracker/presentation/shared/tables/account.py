from dataclasses import dataclass

from portfolio_tracker.application.views import AssetAccountView

from .spec import ColumnSpec, TableSpec, bool_column, text_column


@dataclass(frozen=True, kw_only=True)
class AssetAccountViewTableSpec(TableSpec[AssetAccountView]):
    name = "account"
    title = "Accounts"

    account_id: ColumnSpec = text_column("id", "ID")
    institution_name: ColumnSpec = text_column(
        "institution_connection.institution.name", "Institution"
    )
    account_name: ColumnSpec = text_column("name", "Name")
    external_id: ColumnSpec = text_column("external_id", "External ID")
    is_active: ColumnSpec = bool_column("is_active", "Active")
