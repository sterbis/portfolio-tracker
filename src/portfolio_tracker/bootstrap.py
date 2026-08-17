import os
from typing import Any, TypeVar

from dotenv import load_dotenv

from portfolio_tracker.application.account import (
    AccountCommandService,
    AccountQueryService,
)
from portfolio_tracker.application.fx import FxService
from portfolio_tracker.application.market_data import MarketDataService
from portfolio_tracker.application.persistence import PERSISTED_MODEL_TYPES
from portfolio_tracker.application.portfolio import PortfolioQueryService
from portfolio_tracker.application.shared.exceptions import UserNotLoggedInError
from portfolio_tracker.application.shared.filter import FilterMapper, FilterSplitter
from portfolio_tracker.application.sync import SyncService
from portfolio_tracker.application.transaction import (
    TransactionCommandService,
    TransactionQueryService,
)
from portfolio_tracker.application.user import UserService
from portfolio_tracker.application.views import VIEW_REGISTRY, ViewBuilder
from portfolio_tracker.domain.portfolio import PortfolioBuilder, PortfolioEvaluator
from portfolio_tracker.domain.portfolio.cash_balance import CashBalanceEvaluator
from portfolio_tracker.domain.portfolio.position import PositionEvaluator
from portfolio_tracker.domain.transaction import TransactionAdjuster
from portfolio_tracker.infrastructure.encryption import FernetEncryptor
from portfolio_tracker.infrastructure.fx import FrankfurterClient
from portfolio_tracker.infrastructure.institution import (
    create_institution_registry,
)
from portfolio_tracker.infrastructure.market_data import YahooFinanceClient
from portfolio_tracker.infrastructure.persistence.sqlite import SqliteSessionFactory

TService = TypeVar("TService")


load_dotenv()


class ApplicationContext:
    DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"]

    BASE_CURRENCY = "USD"
    SUPPORTED_CURRENCIES = {"CZK", "EUR", "USD"}
    DEFAULT_REPORTING_CURRENCY = "USD"

    USER_SESSION_TTL = 1800  # 30m = 30 * 60s = 1800s

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


def bootstrap_app(active_user_id: str | None = None) -> ApplicationContext:
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        raise ValueError("'ENCRYPTION_KEY' environment variable not defined.")

    sqlite_db_path = os.getenv("SQLITE_DB_PATH")
    if not sqlite_db_path:
        raise ValueError("'SQLITE_DB_PATH' environment variable not defined.")

    encryptor = FernetEncryptor(encryption_key)

    institution_registry = create_institution_registry()

    session_factory = SqliteSessionFactory(
        database=sqlite_db_path,
        encryptor=encryptor,
        institution_registry=institution_registry,
    )

    fx_client = FrankfurterClient()
    fx_service = FxService(
        fx_client,
        app_base_currency=ApplicationContext.BASE_CURRENCY,
        app_supported_currencies=ApplicationContext.SUPPORTED_CURRENCIES,
    )

    market_data_client = YahooFinanceClient()
    market_data_service = MarketDataService(market_data_client)

    filter_mapper = FilterMapper(registry=VIEW_REGISTRY)
    filter_splitter = FilterSplitter(persisted_model_types=PERSISTED_MODEL_TYPES)
    transaction_adjuster = TransactionAdjuster()
    view_builder = ViewBuilder()

    context = ApplicationContext(active_user_id)
    context.register(
        AccountCommandService,
        AccountCommandService(
            session_factory=session_factory,
            institution_registry=institution_registry,
        ),
    )
    context.register(
        AccountQueryService,
        AccountQueryService(
            session_factory=session_factory,
            filter_mapper=filter_mapper,
            filter_splitter=filter_splitter,
            view_builder=view_builder,
            institution_registry=institution_registry,
        ),
    )
    context.register(UserService, UserService(session_factory=session_factory))
    context.register(
        PortfolioQueryService,
        PortfolioQueryService(
            session_factory=session_factory,
            filter_mapper=filter_mapper,
            filter_splitter=filter_splitter,
            view_builder=view_builder,
            institution_registry=institution_registry,
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
            session_factory=session_factory,
            institution_registry=institution_registry,
            fx_service=fx_service,
            market_data_service=market_data_service,
        ),
    )
    context.register(
        TransactionCommandService,
        TransactionCommandService(
            session_factory=session_factory,
        ),
    )
    context.register(
        TransactionQueryService,
        TransactionQueryService(
            session_factory=session_factory,
            filter_mapper=filter_mapper,
            filter_splitter=filter_splitter,
            view_builder=view_builder,
            institution_registry=institution_registry,
            transaction_adjuster=transaction_adjuster,
        ),
    )

    return context
