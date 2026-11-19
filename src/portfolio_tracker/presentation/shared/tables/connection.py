from dataclasses import dataclass

from portfolio_tracker.application.views import InstitutionConnectionView

from .spec import ColumnSpec, TableSpec, bool_column, date_column, text_column


@dataclass(frozen=True, kw_only=True)
class InstitutionConnectionViewTableSpec(TableSpec[InstitutionConnectionView]):
    name = "institution_connection"
    title = "Connected Institutions"

    connection_id: ColumnSpec = text_column("id", "ID")
    institution_name: ColumnSpec = text_column("institution.name", "Institution")
    connection_name: ColumnSpec = text_column("name", "Name")
    sync_from: ColumnSpec = date_column("sync_from", "Sync From")
    credentials: ColumnSpec = bool_column("credentials", "API Credentials")
