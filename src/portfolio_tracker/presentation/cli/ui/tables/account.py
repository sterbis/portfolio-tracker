from portfolio_tracker.application.views import AssetAccountView

from .view_table import ViewTable, bool_column, text_column


class AssetAccountViewTable(ViewTable[AssetAccountView]):
    name = "account"
    title = "Accounts"

    institution_name = text_column(
        "institution_connection.institution.name", "Institution"
    )
    account_name = text_column("name", "Account")
    external_id = text_column("external_id", "External ID")
    is_active = bool_column("is_active", "Active")
