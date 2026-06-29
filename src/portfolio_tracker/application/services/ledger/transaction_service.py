from dataclasses import replace

from portfolio_tracker.domain.ledger import Transaction
from portfolio_tracker.domain.shared import Money

from portfolio_tracker.application.contracts.commands import (
    CreateTransactionCommand,
    UpdateTransactionCommand,
)
from portfolio_tracker.application.ports.unit_of_work import UnitOfWork


class TransactionService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def create_transaction(self, command: CreateTransactionCommand) -> str:
        payload = command.payload

        transaction = Transaction(
            executed_at=payload.executed_at,
            asset_account_id=payload.asset_account_id,
            type=payload.type,
            instrument_id=payload.instrument_id,
            quantity=payload.quantity,
            price=Money(payload.price.amount, payload.price.currency),
            fee=Money(payload.fee.amount, payload.fee.currency),
            tax=Money(payload.tax.amount, payload.tax.currency),
            cash_impact=Money(payload.cash_impact.amount, payload.cash_impact.currency),
            correlation_id=payload.correlation_id,
        )

        with self._uow as uow:
            if uow.transactions.exists_by_id(transaction.id):
                raise ValueError(f"Transaction already exists: {transaction.id}")

            uow.transactions.add(transaction)
            uow.commit()

        self._update_market_data_streamer(transaction.asset_account_id)
        return transaction.id

    def update_transaction(self, command: UpdateTransactionCommand) -> None:
        with self._uow as uow:
            transaction = uow.transactions.get_by_id(command.transaction_id)
            if not transaction:
                raise ValueError(f"Transaction not foud. ID: {command.transaction_id}")

            payload = command.payload

            updated_transaction = replace(
                transaction,
                executed_at=payload.executed_at,
                asset_account_id=payload.asset_account_id,
                type=payload.type,
                instrument_id=payload.instrument_id,
                quantity=payload.quantity,
                price=Money(payload.price.amount, payload.price.currency),
                fee=Money(payload.fee.amount, payload.fee.currency),
                tax=Money(payload.tax.amount, payload.tax.currency),
                cash_impact=Money(
                    payload.cash_impact.amount, payload.cash_impact.currency
                ),
                correlation_id=payload.correlation_id,
            )

            if updated_transaction.id == transaction.id:
                uow.transactions.update(updated_transaction)
                uow.commit()
                return

            if uow.transactions.exists_by_id(updated_transaction.id):
                raise ValueError(
                    f"Transaction already exists: {updated_transaction.id}"
                )

            uow.transactions.remove_by_id(transaction.id)
            uow.transactions.add(updated_transaction)
            uow.commit()

        self._update_market_data_streamer(transaction.asset_account_id)

        if updated_transaction.asset_account_id != transaction.asset_account_id:
            self._update_market_data_streamer(updated_transaction.asset_account_id)

    def delete_transaction(self, transaction_id: str) -> None:
        with self._uow as uow:
            transaction = uow.transactions.get_by_id(transaction_id)
            if not transaction:
                raise ValueError(f"Transaction not foud. ID: {transaction_id}")

            uow.transactions.remove_by_id(transaction_id)
            uow.commit()

        self._update_market_data_streamer(transaction.asset_account_id)

    def _update_market_data_streamer(self, asset_account_id: str) -> None:
        pass
