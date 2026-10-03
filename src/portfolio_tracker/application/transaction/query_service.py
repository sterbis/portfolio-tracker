from datetime import date

from filterutils import FilterNode, FilterTree, Operator

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import StorageReadConnection
from portfolio_tracker.application.shared.filter import FilterMapper, FilterSplitter
from portfolio_tracker.application.shared.service import QueryService
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
        storage_connection: StorageReadConnection,
        filter_mapper: FilterMapper,
        filter_splitter: FilterSplitter,
        view_builder: ViewBuilder,
        institution_registry: InstitutionRegistry,
        transaction_adjuster: TransactionAdjuster,
    ) -> None:
        super().__init__(
            storage_connection, filter_mapper, filter_splitter, view_builder
        )
        self._institution_registry = institution_registry
        self._transaction_adjuster = transaction_adjuster

    def get_transaction(
        self, user_id: str, transaction_id: str
    ) -> TransactionPlainView:
        with self._unit_of_work(user_id) as uow:
            transaction = uow.transactions.get_by_id_required(transaction_id)
            return TransactionPlainView.from_domain(transaction)

    def get_transactions(
        self, user_id: str, query: GetTransactionsQuery
    ) -> list[TransactionView]:
        repository_filter, memory_filter = self._resolve_filters(query.filter)

        with self._unit_of_work(user_id) as uow:
            account_map = uow.accounts.get_account_map(user_id)
            required_account_ids = account_map.resolve_account_ids(
                query.connection_ids, query.account_ids
            )
            transactions = uow.transactions.get(
                filter_=FilterTree.and_combine(
                    repository_filter,
                    (
                        FilterNode(
                            "account_id", Operator.IN, required_account_ids, Transaction
                        )
                        if required_account_ids
                        else None
                    ),
                ),
            )

            transaction_dates: set[date] = set()
            account_ids: set[str] = set()
            instrument_ids: set[str] = set()
            for transaction in transactions:
                transaction_dates.add(transaction.executed_at.date())
                account_ids.add(transaction.account_id)
                if transaction.instrument_id:
                    instrument_ids.add(transaction.instrument_id)

            splits_list = uow.market_data.get_stock_splits_by_instrument_ids(
                instrument_ids
            )
            adjusted_transactions = self._transaction_adjuster.adjust(
                transactions, splits_list
            )

            rates_by_date = uow.fx_rates.get_by_dates_required(transaction_dates)
            converter = TransactionConverter(rates_by_date)
            converted_transactions = list(
                converter.convert_many(adjusted_transactions, query.reporting_currency)
            )
            if memory_filter:
                converted_transactions = list(
                    memory_filter.apply(converted_transactions)
                )

            instruments = uow.instruments.get_by_ids(instrument_ids)
            accounts = uow.accounts.get_by_ids(account_ids)
            connections = uow.institution_connections.get_by_ids(
                {account.institution_connection_id for account in accounts}
            )
            institutions = [
                self._institution_registry.get_institution(connection.institution_id)
                for connection in connections
            ]

            views = self._view_builder.build_transaction_views(
                institutions,
                connections,
                accounts,
                instruments,
                converted_transactions,
            )
            return self._apply_view_options(
                views, sorts=query.sorts, offset=query.offset, limit=query.limit
            )
