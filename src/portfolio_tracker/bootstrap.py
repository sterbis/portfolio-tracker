import os
from typing import Any, TypeVar

from dotenv import load_dotenv

from portfolio_tracker.application.account import (
    AccountCommandService,
    AccountQueryService,
)
from portfolio_tracker.application.fx import FxService
from portfolio_tracker.application.market_data import MarketDataService
from portfolio_tracker.application.portfolio import PortfolioQueryService
from portfolio_tracker.application.sync import SyncService
from portfolio_tracker.application.transaction import (
    TransactionCommandService,
    TransactionQueryService,
)
from portfolio_tracker.application.user import AuthService, UserNotLoggedInError

from portfolio_tracker.domain.portfolio import PortfolioBuilder, PortfolioEvaluator
from portfolio_tracker.domain.portfolio.cash_balance import CashBalanceEvaluator
from portfolio_tracker.domain.portfolio.position import PositionEvaluator
from portfolio_tracker.domain.transaction import TransactionAdjuster

from portfolio_tracker.infrastructure.encryption import FernetEncryptor
from portfolio_tracker.infrastructure.fx import FrankfurterClient
from portfolio_tracker.infrastructure.institution import (
    create_client,
    create_parser,
    create_registry,
)
from portfolio_tracker.infrastructure.market_data import YahooFinanceClient
from portfolio_tracker.infrastructure.persistence.sqlite import SqliteUnitOfWork

TService = TypeVar("TService")


load_dotenv()


class AppContext:
    DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"]
    SESSION_TTL = 1800  # 30m = 30 * 60s = 1800s

    def __init__(self, active_user_id: str | None = None) -> None:
        self._active_user_id = active_user_id
        self._services: dict[type[Any], Any] = {}

    @property
    def active_user_id(self) -> str:
        if not self._active_user_id:
            raise UserNotLoggedInError()

        return self._active_user_id

    def register(self, type_: type[TService], service: TService) -> None:
        self._services[type_] = service

    def get(self, type_: type[TService]) -> TService:
        service: TService = self._services[type_]
        return service


def bootstrap_app(active_user_id: str | None = None) -> AppContext:
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        raise ValueError("'ENCRYPTION_KEY' environment variable not defined.")

    sqlite_db_path = os.getenv("SQLITE_DB_PATH")
    if not sqlite_db_path:
        raise ValueError("'SQLITE_DB_PATH' environment variable not defined.")

    encryptor = FernetEncryptor(encryption_key)

    institution_registry = create_registry()

    read_uow = SqliteUnitOfWork(
        sqlite_db_path, encryptor, institution_registry, read_only=True
    )
    write_uow = SqliteUnitOfWork(
        sqlite_db_path, encryptor, institution_registry, read_only=False
    )

    fx_client = FrankfurterClient()
    fx_service = FxService(
        fx_client,
        app_base_currency="USD",
        app_supported_currencies={"CZK", "EUR", "USD"},
    )

    market_data_client = YahooFinanceClient()
    market_data_service = MarketDataService(market_data_client)

    transaction_adjuster = TransactionAdjuster()

    context = AppContext(active_user_id)
    context.register(
        AccountCommandService, AccountCommandService(
            institution_registry=institution_registry,
            uow=write_uow,
            client_factory=create_client,
        )
    )
    context.register(
        AccountQueryService, AccountQueryService(
            institution_registry=institution_registry,
            uow=read_uow,
        )
    )
    context.register(AuthService, AuthService(uow=write_uow))
    context.register(
        PortfolioQueryService,
        PortfolioQueryService(
            institution_registry=institution_registry,
            uow=read_uow,
            transaction_adjuster=transaction_adjuster,
            portfolio_builder=PortfolioBuilder(),
            portfolio_evaluator=PortfolioEvaluator(
                cash_balance_evaluator=CashBalanceEvaluator(),
                position_evaluator=PositionEvaluator(),
            ),
            fx_service=fx_service,
            market_data_service=market_data_service,
        ),
    )
    context.register(
        SyncService,
        SyncService(
            uow=write_uow,
            fx_service=fx_service,
            market_data_service=market_data_service,
            client_factory=create_client,
            parser_factory=create_parser,
        ),
    )
    context.register(
        TransactionCommandService,
        TransactionCommandService(
            uow=write_uow,
        ),
    )
    context.register(
        TransactionQueryService,
        TransactionQueryService(
            institution_registry=institution_registry,
            uow=read_uow,
            transaction_adjuster=transaction_adjuster,
        ),
    )

    return context
