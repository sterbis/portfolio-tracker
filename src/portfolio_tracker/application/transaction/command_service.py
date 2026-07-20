from dataclasses import replace

from portfolio_tracker.application.contracts.commands import (
    CreateTransactionCommand,
    UpdateTransactionCommand,
)
from portfolio_tracker.application.persistence import SessionFactory
from portfolio_tracker.domain.shared import Money
from portfolio_tracker.domain.transaction import Transaction


class TransactionCommandService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

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

        with self._session_factory.create() as session, session.unit_of_work() as uow:
            if uow.transactions.exists_by_checksum(transaction.checksum):
                raise ValueError(f"Transaction already exists: {transaction.id}")

            uow.transactions.add(transaction)
            uow.commit()

        self._update_market_data_streamer(transaction.asset_account_id)
        return transaction.id

    def update_transaction(self, command: UpdateTransactionCommand) -> None:
        with self._session_factory.create() as session, session.unit_of_work() as uow:
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

            if updated_transaction.checksum == transaction.checksum:
                uow.transactions.update(updated_transaction)
                uow.commit()
                return

            if uow.transactions.exists_by_checksum(updated_transaction.checksum):
                raise ValueError(
                    f"Transaction already exists: {updated_transaction.checksum}"
                )

            uow.transactions.remove_by_id(transaction.id)
            uow.transactions.add(updated_transaction)
            uow.commit()

        self._update_market_data_streamer(transaction.asset_account_id)

        if updated_transaction.asset_account_id != transaction.asset_account_id:
            self._update_market_data_streamer(updated_transaction.asset_account_id)

    def delete_transaction(self, transaction_id: str) -> None:
        with self._session_factory.create() as session, session.unit_of_work() as uow:
            transaction = uow.transactions.get_by_id(transaction_id)
            if not transaction:
                raise ValueError(f"Transaction not foud. ID: {transaction_id}")

            uow.transactions.remove_by_id(transaction_id)
            uow.commit()

        self._update_market_data_streamer(transaction.asset_account_id)

    def _update_market_data_streamer(self, asset_account_id: str) -> None:
        pass
