from portfolio_tracker.application.persistence import UnitOfWork
from portfolio_tracker.application.shared.errors import (
    AssetAccountNotFoundError,
    InstrumentNotFoundError,
    TransactionAlreadyExistsError,
)
from portfolio_tracker.application.shared.service import CommandService
from portfolio_tracker.domain.shared import Money
from portfolio_tracker.domain.transaction import Transaction

from .commands import (
    CreateTransactionCommand,
    UpdateTransactionCommand,
)


class TransactionCommandService(CommandService):
    def create_transaction(
        self, user_id: str, command: CreateTransactionCommand
    ) -> str:
        payload = command.payload

        transaction = Transaction(
            correlation_id=payload.correlation_id,
            executed_at=payload.executed_at,
            account_id=payload.account_id,
            type=payload.type,
            instrument_id=payload.instrument_id,
            quantity=payload.quantity,
            price=Money(payload.price.amount, payload.price.currency),
            fee=Money(payload.fee.amount, payload.fee.currency),
            tax=Money(payload.tax.amount, payload.tax.currency),
            cash_impact=Money(payload.cash_impact.amount, payload.cash_impact.currency),
        )

        with self._unit_of_work(user_id) as uow:
            self._validate_transaction(uow, transaction)
            uow.transactions.add(transaction)
            uow.commit()

        return transaction.id

    def update_transaction(
        self, user_id: str, command: UpdateTransactionCommand
    ) -> None:
        with self._unit_of_work(user_id) as uow:
            transaction = uow.transactions.get_by_id_required(command.transaction_id)

            payload = command.payload
            updated_transaction = Transaction(
                correlation_id=payload.correlation_id,
                executed_at=payload.executed_at,
                account_id=payload.account_id,
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

            if updated_transaction.id == transaction.id:
                uow.transactions.update_required(updated_transaction)
                uow.commit()
                return

            self._validate_transaction(uow, updated_transaction)

            uow.transactions.remove_by_id_required(transaction.id)
            uow.transactions.add(updated_transaction)
            uow.commit()

    def delete_transaction(self, user_id: str, transaction_id: str) -> None:
        with self._unit_of_work(user_id) as uow:
            uow.transactions.remove_by_id_required(transaction_id)
            uow.commit()

    def _validate_transaction(self, uow: UnitOfWork, transaction: Transaction) -> None:
        if uow.transactions.exists(transaction.id):
            raise TransactionAlreadyExistsError(transaction_id=transaction.id)

        if not uow.accounts.is_user_account(transaction.account_id):
            raise AssetAccountNotFoundError(transaction.account_id)

        if transaction.instrument_id and not uow.instruments.exists(transaction.instrument_id):
            raise InstrumentNotFoundError(transaction.instrument_id)
