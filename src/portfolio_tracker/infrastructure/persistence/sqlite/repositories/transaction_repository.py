from datetime import date
from functools import cached_property
from typing import Any

from filterutils import Filter, FilterNode, FilterTree, Operator

from portfolio_tracker.application.persistence import TransactionRepository
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.account import AssetAccount
from portfolio_tracker.domain.institution import InstitutionConnection
from portfolio_tracker.domain.transaction import Transaction, TransactionType
from portfolio_tracker.infrastructure.persistence.sqlite.executor import (
    Row,
    SqliteExecutor,
)
from portfolio_tracker.infrastructure.persistence.sqlite.registry import FieldReference


class SqliteTransactionRepository(TransactionRepository):
    def __init__(self, user_id: str, executor: SqliteExecutor) -> None:
        super().__init__(user_id)
        self._executor = executor

    @cached_property
    def _user_account_ids(self) -> set[str]:
        account_id_field = FieldReference(AssetAccount, "id")
        rows = self._executor.select(
            model=AssetAccount,
            fields=[account_id_field],
            filter_=FilterNode(
                "user_id", Operator.EQ, self._user_id, InstitutionConnection
            ),
        )
        return {row[account_id_field] for row in rows}

    @cached_property
    def _scope_filter(self) -> Filter:
        return FilterNode("account_id", Operator.IN, self._user_account_ids, Transaction)

    def add(self, transaction: Transaction) -> None:
        self._executor.insert(
            model=Transaction,
            values=self._transaction_to_values(transaction),
        )

    def ensure(self, transaction: Transaction) -> None:
        self._executor.insert_on_conflict_do_nothing(
            model=Transaction,
            values=self._transaction_to_values(transaction),
            conflict_field_names=["id"],
        )

    def get(
        self,
        *,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Transaction]:
        rows = self._executor.select(
            model=Transaction,
            filter_=FilterTree.and_combine(filter_, self._scope_filter),
            sorts=sorts,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_transaction(row) for row in rows]

    def get_by_id(self, transaction_id: str) -> Transaction | None:
        transactions = self.get(
            filter_=FilterNode("id", Operator.EQ, transaction_id, Transaction),
        )
        return transactions[0] if transactions else None

    def get_distinct_dates(self, filter_: Filter | None = None) -> set[date]:
        executed_at_field = FieldReference(Transaction, "executed_at")
        rows = self._executor.select(
            model=Transaction,
            fields=[executed_at_field],
            distinct=True,
            filter_=FilterTree.and_combine(filter_, self._scope_filter),
        )
        return {row[executed_at_field].date() for row in rows}

    def get_distinct_instrument_ids(self, filter_: Filter | None = None) -> set[str]:
        instrument_id_field = FieldReference(Transaction, "instrument_id")
        rows = self._executor.select(
            model=Transaction,
            fields=[instrument_id_field],
            distinct=True,
            filter_=FilterTree.and_combine(filter_, self._scope_filter),
        )
        return {
            row[instrument_id_field]
            for row in rows
            if row[instrument_id_field] is not None
        }

    def update(self, transaction: Transaction) -> int:
        cursor = self._executor.update(
            model=Transaction,
            values=self._transaction_to_values(transaction),
            filter_=FilterTree(
                FilterNode("id", Operator.EQ, transaction.id, Transaction),
                self._scope_filter,
            ),
        )
        return cursor.rowcount

    def remove(self, filter_: Filter) -> int:
        cursor = self._executor.delete(
            model=Transaction,
            filter_=FilterTree(filter_, self._scope_filter),
        )
        return cursor.rowcount

    def remove_by_id(self, transaction_id: str) -> int:
        return self.remove(
            filter_=FilterTree(
                FilterNode("id", Operator.EQ, transaction_id, Transaction),
                self._scope_filter,
            ),
        )

    def remove_by_account_id(self, account_id: str) -> int:
        return self.remove(
            filter_=FilterTree(
                FilterNode("account_id", Operator.EQ, account_id, Transaction),
                self._scope_filter,
            ),
        )

    def exists(self, transaction_id: str) -> bool:
        return self.get_by_id(transaction_id) is not None

    def _transaction_to_values(self, transaction: Transaction) -> dict[str, Any]:
        return {
            "id": transaction.id,
            "correlation_id": transaction.correlation_id,
            "executed_at": transaction.executed_at,
            "account_id": transaction.account_id,
            "type": transaction.type,
            "instrument_id": transaction.instrument_id,
            "quantity": transaction.quantity,
            "price": transaction.price,
            "fee": transaction.fee,
            "tax": transaction.tax,
            "cash_impact": transaction.cash_impact,
        }

    def _row_to_transaction(self, row: Row) -> Transaction:
        def field(name: str) -> FieldReference:
            return FieldReference(Transaction, name)

        return Transaction(
            provided_id=row[field("id")],
            correlation_id=row[field("correlation_id")],
            executed_at=row[field("executed_at")],
            account_id=row[field("account_id")],
            type=TransactionType(row[field("type")]),
            instrument_id=row[field("instrument_id")],
            quantity=row[field("quantity")],
            price=row[field("price")],
            fee=row[field("fee")],
            tax=row[field("tax")],
            cash_impact=row[field("cash_impact")],
        )
