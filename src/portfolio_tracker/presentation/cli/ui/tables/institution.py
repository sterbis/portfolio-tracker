from portfolio_tracker.application.views import InstitutionConnectionView

from .view_table import ViewTable, bool_column, date_column, text_column


class InstitutionConnectionViewTable(ViewTable[InstitutionConnectionView]):
    name = "institution_connection"
    title = "Connected Institutions"

    institution_id = text_column("institution.name", "Institution ID")
    institution_name = text_column("institution.name", "Institution")
    connection_name = text_column("name", "Name")
    account_opened_on = date_column("account_opened_on", "Account Opened On")
    credentials = bool_column("credentials", "API Credentials")
