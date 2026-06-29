from datetime import date

from portfolio_tracker.domain.ledger import TransactionAdjuster
from portfolio_tracker.application.contracts.dtos import TransactionDto
from portfolio_tracker.application.contracts.dto_assembler import DtoAssembler
from portfolio_tracker.application.contracts.queries import GetTransactionsQuery
from portfolio_tracker.application.ports.unit_of_work import UnitOfWork
from portfolio_tracker.application.services.accounts import SUPPORTED_INSTITUTIONS


class TransactionQueryService:
    def __init__(
        self,
        uow: UnitOfWork,
        transaction_adjuster: TransactionAdjuster,
    ) -> None:
        self._uow = uow
        self._transaction_adjuster = transaction_adjuster

    def execute(self, query: GetTransactionsQuery) -> list[TransactionDto]:
        with self._uow as uow:
            transactions = uow.transactions.get(
                filter_=query.filter,
                order_by=query.order_by,
                limit=query.limit,
                offset=query.offset,
            )

            dates: set[date] = set()
            asset_account_ids: set[str] = set()
            instrument_ids: set[str] = set()
            for transaction in transactions:
                dates.add(transaction.executed_at.date())
                asset_account_ids.add(transaction.asset_account_id)
                if transaction.instrument_id:
                    instrument_ids.add(transaction.instrument_id)

            splits_list = uow.market_data.get_stock_splits_by_instrument_ids(
                instrument_ids
            )
            transactions = list(
                self._transaction_adjuster.adjust(transactions, splits_list)
            )
            rates_by_date = uow.fx_rates.get_required_rates_by_date_map(dates)

            asset_accounts = uow.accounts.get_asset_accounts_by_ids(asset_account_ids)
            institution_accounts = uow.accounts.get_institution_accounts_by_ids(
                {
                    asset_account.institution_account_id
                    for asset_account in asset_accounts
                }
            )
            institutions = [
                SUPPORTED_INSTITUTIONS[institution_account.institution_id]
                for institution_account in institution_accounts
            ]
            instruments = uow.instruments.get_by_ids(instrument_ids)

        return DtoAssembler().assemble_transactions(
            institutions,
            institution_accounts,
            asset_accounts,
            instruments,
            transactions,
            rates_by_date,
            query.reporting_currency,
        )
