from dataclasses import dataclass

from portfolio_tracker.application.account import (
    AccountCommandService,
    AccountQueryService,
)
from portfolio_tracker.application.institution import (
    InstitutionCommandService,
    InstitutionQueryService,
)
from portfolio_tracker.application.portfolio import PortfolioQueryService
from portfolio_tracker.application.sync import SyncService
from portfolio_tracker.application.transaction import (
    TransactionCommandService,
    TransactionQueryService,
)
from portfolio_tracker.application.user import UserService


@dataclass(frozen=True)
class Container:
    account_command_service: AccountCommandService
    account_query_service: AccountQueryService
    institution_command_service: InstitutionCommandService
    institution_query_service: InstitutionQueryService
    portfolio_query_service: PortfolioQueryService
    sync_service: SyncService
    transaction_command_service: TransactionCommandService
    transaction_query_service: TransactionQueryService
    user_service: UserService
