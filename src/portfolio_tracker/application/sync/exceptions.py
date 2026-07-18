from portfolio_tracker.application.contracts.exceptions import AppError


class SyncError(AppError):
    _message_template = "Failed to sync {institution_account_name} ({institution_account_id}) institution account."

    def __init__(self, institution_account_id: str, institution_account_name: str) -> None:
        super().__init__(
            institution_account_id=institution_account_id,
            institution_account_name=institution_account_name,
        )


class FetchReportError(SyncError):
    _message_template = "Failed to fetch {institution_account_name} ({institution_account_id}) institution account report."


class ParseReportError(SyncError):
    _message_template = "Failed to parse {institution_account_name} ({institution_account_id}) institution account report."
