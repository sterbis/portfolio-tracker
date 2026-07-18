from portfolio_tracker.application.contracts.exceptions import AppError


class MarketDataClientError(Exception): ...


class MarketDataIntegrityError(AppError):
    _message_template = "Market Data Integrity Error: {detail}"

    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail)
