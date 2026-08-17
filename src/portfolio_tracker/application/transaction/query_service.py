from datetime import date

from portfolio_tracker.application.institution import InstitutionRegistry
from portfolio_tracker.application.persistence import SessionFactory
from portfolio_tracker.application.shared.filter import FilterMapper, FilterSplitter
from portfolio_tracker.application.shared.order_by import OrderBy
from portfolio_tracker.application.shared.service import ApplicationQueryService
from portfolio_tracker.application.views import TransactionView, ViewBuilder
from portfolio_tracker.domain.transaction import (
    Transaction,
    TransactionAdjuster,
    TransactionConverter,
)

from .queries import GetTransactionsQuery


class TransactionQueryService(ApplicationQueryService):
    DEFAULT_ORDER_BY: OrderBy = OrderBy("executed_at", Transaction, "ASC")

    def __init__(
        self,
        session_factory: SessionFactory,
        filter_mapper: FilterMapper,
        filter_splitter: FilterSplitter,
        view_builder: ViewBuilder,
        institution_registry: InstitutionRegistry,
        transaction_adjuster: TransactionAdjuster,
    ) -> None:
        super().__init__(session_factory, filter_mapper, filter_splitter, view_builder)
        self._institution_registry = institution_registry
        self._transaction_adjuster = transaction_adjuster

    def get_transactions(
        self, user_id: str, query: GetTransactionsQuery
    ) -> list[TransactionView]:
        with self._user_unit_of_work(user_id, read_only=True) as uow:
            transactions = uow.transactions.get(
                institution_account_ids=query.institution_account_ids,
                asset_account_ids=query.asset_account_ids,
                filter_=query.filter,
                order_by_list=query.order_by_list or [self.DEFAULT_ORDER_BY],
                limit=query.limit,
                offset=query.offset,
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

            instruments = uow.instruments.get_by_ids(instrument_ids)

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

            return self._view_builder.build_transaction_views(
                institutions,
                institution_accounts,
                asset_accounts,
                instruments,
                converted_transactions,
            )
