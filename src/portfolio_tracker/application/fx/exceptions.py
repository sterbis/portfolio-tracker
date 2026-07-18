from portfolio_tracker.application.contracts.exceptions import AppError


class FxClientError(Exception): ...


class FxDataIntegrityError(AppError):
    _message_template = "Fx Data Integrity Error: {detail}"

    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail)
