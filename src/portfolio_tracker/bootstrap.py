from portfolio_tracker.application.account import (
    AccountCommandService,
    AccountQueryService,
)
from portfolio_tracker.application.container import Container
from portfolio_tracker.application.fx import FxService
from portfolio_tracker.application.institution import (
    InstitutionCommandService,
    InstitutionQueryService,
)
from portfolio_tracker.application.market_data import MarketDataService
from portfolio_tracker.application.persistence import PERSISTED_MODEL_TYPES
from portfolio_tracker.application.portfolio import PortfolioQueryService
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
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.domain.transaction import TransactionAdjuster
from portfolio_tracker.infrastructure.configuration import (
    APP_BASE_CURRENCY,
    Configuration,
)
from portfolio_tracker.infrastructure.fx import FrankfurterClient
from portfolio_tracker.infrastructure.institution import create_institution_registry
from portfolio_tracker.infrastructure.market_data import YahooFinanceClient
from portfolio_tracker.infrastructure.persistence.storage import initialize_storage
from portfolio_tracker.infrastructure.security import (
    BcryptPasswordHasher,
    FernetEncryptor,
)
from portfolio_tracker.shared.settings_utils import JsonSettingsStore, SettingsCache

from .settings import Settings


def bootstrap(
    configuration: Configuration,
) -> tuple[Container, SettingsCache[Settings]]:
    encryptor = FernetEncryptor(configuration.encryption_key)
    institution_registry = create_institution_registry()

    storage_read_connection_factory, storage_connection_factory = initialize_storage(
        type_=configuration.storage_type,
        uri=configuration.storage_uri,
        institution_registry=institution_registry,
        encryptor=encryptor,
    )

    fx_client = FrankfurterClient()
    fx_service = FxService(
        base_currency=APP_BASE_CURRENCY,
        quote_currencies={
            currency for currency in Currency if currency != APP_BASE_CURRENCY
        },
        fx_client=fx_client,
    )

    market_data_client = YahooFinanceClient()
    market_data_service = MarketDataService(market_data_client)

    filter_mapper = FilterMapper(view_registry=VIEW_REGISTRY)
    filter_splitter = FilterSplitter(persisted_model_types=PERSISTED_MODEL_TYPES)
    transaction_adjuster = TransactionAdjuster()
    view_builder = ViewBuilder()

    container = Container(
        account_command_service=AccountCommandService(
            storage_connection_factory=storage_connection_factory,
            institution_registry=institution_registry,
        ),
        account_query_service=AccountQueryService(
            storage_connection_factory=storage_read_connection_factory,
            filter_mapper=filter_mapper,
            filter_splitter=filter_splitter,
            view_builder=view_builder,
            institution_registry=institution_registry,
        ),
        institution_command_service=InstitutionCommandService(
            storage_connection_factory=storage_connection_factory,
            institution_registry=institution_registry,
        ),
        institution_query_service=InstitutionQueryService(
            storage_connection_factory=storage_read_connection_factory,
            filter_mapper=filter_mapper,
            filter_splitter=filter_splitter,
            view_builder=view_builder,
            institution_registry=institution_registry,
        ),
        portfolio_query_service=PortfolioQueryService(
            storage_connection_factory=storage_read_connection_factory,
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
        sync_service=SyncService(
            storage_connection_factory=storage_connection_factory,
            institution_registry=institution_registry,
            fx_service=fx_service,
            market_data_service=market_data_service,
        ),
        transaction_command_service=TransactionCommandService(
            storage_connection_factory=storage_connection_factory,
        ),
        transaction_query_service=TransactionQueryService(
            storage_connection_factory=storage_read_connection_factory,
            filter_mapper=filter_mapper,
            filter_splitter=filter_splitter,
            view_builder=view_builder,
            institution_registry=institution_registry,
            transaction_adjuster=transaction_adjuster,
        ),
        user_service=UserService(
            storage_connection_factory=storage_connection_factory,
            password_hasher=BcryptPasswordHasher(),
        ),
    )

    settings = SettingsCache(
        store=JsonSettingsStore(
            settings_dir=configuration.users_settings_dir,
            settings_cls=Settings,
        ),
        default_settings=Settings(),
    )

    return container, settings
