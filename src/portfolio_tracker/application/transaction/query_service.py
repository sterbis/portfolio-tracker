from datetime import date

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import StorageConnectionFactory
from portfolio_tracker.application.shared.errors import TransactionNotFoundError
from portfolio_tracker.application.shared.filter import FilterMapper, FilterSplitter
from portfolio_tracker.application.shared.service import QueryService
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.application.views import (
    TransactionPlainView,
    TransactionView,
    ViewBuilder,
)
from portfolio_tracker.domain.transaction import (
    Transaction,
    TransactionAdjuster,
    TransactionConverter,
)

from .queries import GetTransactionsQuery


class TransactionQueryService(QueryService):
    def __init__(
        self,
        storage_connection_factory: StorageConnectionFactory,
        filter_mapper: FilterMapper,
        filter_splitter: FilterSplitter,
        view_builder: ViewBuilder,
        institution_registry: InstitutionRegistry,
        transaction_adjuster: TransactionAdjuster,
    ) -> None:
        super().__init__(
            storage_connection_factory, filter_mapper, filter_splitter, view_builder
        )
        self._institution_registry = institution_registry
        self._transaction_adjuster = transaction_adjuster

    def get_transaction(
        self, user_id: str, transaction_id: str
    ) -> TransactionPlainView:
        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            transaction = uow.transactions.get_by_id(transaction_id)
            if transaction is None:
                raise TransactionNotFoundError(transaction_id)

            return TransactionPlainView.from_domain(transaction)

    def get_transactions(
        self, user_id: str, query: GetTransactionsQuery
    ) -> list[TransactionView]:
        repository_filter, memory_filter = self._resolve_filters(query.filter)

        with self._user_scoped_unit_of_work(user_id, read_only=True) as uow:
            transactions = uow.transactions.get(
                institution_account_ids=query.institution_account_ids,
                asset_account_ids=query.asset_account_ids,
                filter_=repository_filter,
            )

            transaction_dates: set[date] = set()
            instrument_ids: set[str] = set()
            for transaction in transactions:
                transaction_dates.add(transaction.executed_at.date())
                if transaction.instrument_id:
                    instrument_ids.add(transaction.instrument_id)

            splits_list = uow.market_data.get_stock_splits_by_instrument_ids(
                instrument_ids
            )
            adjusted_transactions = self._transaction_adjuster.adjust(
                transactions, splits_list
            )

            rates_by_date = uow.fx_rates.get_required_rates_by_date_map(
                transaction_dates
            )
            converter = TransactionConverter(rates_by_date)
            converted_transactions = converter.convert_many(
                adjusted_transactions, query.reporting_currency
            )
            if memory_filter:
                converted_transactions = memory_filter.apply(converted_transactions)

            instruments = uow.instruments.get_by_ids(
                {
                    converted_transaction.instrument_id
                    for converted_transaction in converted_transactions
                    if converted_transaction.instrument_id
                }
            )

            asset_account_ids = uow.accounts_map.resolve_asset_account_ids(
                query.institution_account_ids, query.asset_account_ids
            )
            asset_accounts = uow.accounts.get_asset_accounts_by_ids(asset_account_ids)
            institution_accounts = uow.accounts.get_institution_accounts_by_ids(
                {
                    asset_account.institution_account_id
                    for asset_account in asset_accounts
                }
            )
            institutions = [
                self._institution_registry.get_institution(
                    institution_account.institution_id
                )
                for institution_account in institution_accounts
            ]

            views = self._view_builder.build_transaction_views(
                institutions,
                institution_accounts,
                asset_accounts,
                instruments,
                converted_transactions,
            )

            return self._apply_view_options(
                views, sorts=query.sorts, offset=query.offset, limit=query.limit
            )
