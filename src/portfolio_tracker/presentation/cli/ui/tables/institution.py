from portfolio_tracker.application.views import InstitutionConnectionView

from .view_table import ViewTable, bool_column, date_column, text_column


class InstitutionConnectionViewTable(ViewTable[InstitutionConnectionView]):
    name = "institution_connection"
    title = "Connected Institutions"

    institution_name = text_column("institution.name", "Institution")
    connection_id = text_column("id", "Connection ID")
    connection_name = text_column("name", "Connection")
    sync_from = date_column("sync_from", "Sync From")
    credentials = bool_column("credentials", "API Credentials")
