from portfolio_tracker.application.shared.exceptions import (
    TransactionAlreadyExistsError,
    TransactionNotFoundError,
)
from portfolio_tracker.application.shared.service import ApplicationService
from portfolio_tracker.domain.shared import Money
from portfolio_tracker.domain.transaction import Transaction

from .commands import (
    CreateTransactionCommand,
    UpdateTransactionCommand,
)


class TransactionCommandService(ApplicationService):
    def create_transaction(
        self, user_id: str, command: CreateTransactionCommand
    ) -> str:
        payload = command.payload

        transaction = Transaction(
            correlation_id=payload.correlation_id,
            executed_at=payload.executed_at,
            asset_account_id=payload.asset_account_id,
            type=payload.type,
            instrument_id=payload.instrument_id,
            quantity=payload.quantity,
            price=Money(payload.price.amount, payload.price.currency),
            fee=Money(payload.fee.amount, payload.fee.currency),
            tax=Money(payload.tax.amount, payload.tax.currency),
            cash_impact=Money(payload.cash_impact.amount, payload.cash_impact.currency),
        )

        with self._user_unit_of_work(user_id) as uow:
            if uow.transactions.exists(transaction):
                raise TransactionAlreadyExistsError(transaction_id=transaction.id)

            uow.transactions.add(transaction)
            uow.commit()

        return transaction.id

    def update_transaction(
        self, user_id: str, command: UpdateTransactionCommand
    ) -> None:
        with self._user_unit_of_work(user_id) as uow:
            transaction = uow.transactions.get_by_id(command.transaction_id)
            if not transaction:
                raise TransactionNotFoundError(command.transaction_id)

            payload = command.payload
            updated_transaction = Transaction(
                id=command.transaction_id,
                correlation_id=payload.correlation_id,
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
            )

            if updated_transaction.checksum == transaction.checksum:
                uow.transactions.update(updated_transaction)
                uow.commit()
                return

            if uow.transactions.exists(updated_transaction):
                raise TransactionAlreadyExistsError(
                    transaction_id=updated_transaction.id
                )

            uow.transactions.remove_by_id(transaction.id)
            uow.transactions.add(updated_transaction)
            uow.commit()

    def delete_transaction(self, user_id: str, transaction_id: str) -> None:
        with self._user_unit_of_work(user_id) as uow:
            transaction = uow.transactions.get_by_id(transaction_id)
            if not transaction:
                raise TransactionNotFoundError(transaction_id)

            uow.transactions.remove_by_id(transaction_id)
            uow.commit()
