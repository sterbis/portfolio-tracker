import sqlite3
from datetime import date
from typing import Any, Literal

from filterutils import Filter, FilterNode, Operator

from portfolio_tracker.application.ports.repositories import TransactionRepository
from portfolio_tracker.domain.ledger import Transaction, TransactionType

from ..executor import SqliteExecutor


class SqliteTransactionRepository(TransactionRepository):
    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def add(self, transaction: Transaction) -> None:
        self._executor.insert(
            table="ledger_entry",
            values=self._transaction_to_values(transaction),
        )

    def ensure(self, transaction: Transaction) -> None:
        self._executor.insert_if_not_exists(
            table="ledger_entry",
            values=self._transaction_to_values(transaction),
            conflict_columns=["checksum"],
        )

    def get(
        self,
        *,
        filter_: Filter | None = None,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Transaction]:
        rows = self._executor.select(
            table="ledger_entry",
            filter_=filter_,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_transaction(row) for row in rows]

    def get_by_id(self, transaction_id: str) -> Transaction | None:
        row = self._executor.select_one(
            table="ledger_entry",
            filter_=FilterNode("transaction_id", Operator.EQ, transaction_id),
        )
        return self._row_to_transaction(row) if row else None

    def get_distinct_dates(self, filter_: Filter | None = None) -> set[date]:
        rows = self._executor.select(
            table="ledger_entry",
            columns=["executed_at"],
            distinct=True,
            filter_=filter_,
        )
        return {row["executed_at"].date() for row in rows}

    def get_distinct_instrument_ids(self, filter_: Filter | None = None) -> set[str]:
        rows = self._executor.select(
            table="ledger_entry",
            columns=["instrument_id"],
            distinct=True,
            filter_=filter_,
        )
        return {row["instrument_id"] for row in rows}

    def update(self, transaction: Transaction) -> None:
        self._executor.update(
            table="ledger_entry",
            values=self._transaction_to_values(transaction),
            filter_=FilterNode("transaction_id", Operator.EQ, transaction.id),
        )

    def remove_by_id(self, transaction_id: str) -> None:
        self._executor.delete(
            table="ledger_entry",
            filter_=FilterNode("transaction_id", Operator.EQ, transaction_id),
        )

    def exists_by_checksum(self, checksum: str) -> bool:
        row = self._executor.select_one(
            table="ledger_entry",
            columns=["1"],
            filter_=FilterNode("checksum", Operator.EQ, checksum),
            limit=1,
        )
        return row is not None

    def _transaction_to_values(self, transaction: Transaction) -> dict[str, Any]:
        return {
            "executed_at": transaction.executed_at,
            "asset_account_id": transaction.asset_account_id,
            "type": transaction.type,
            "instrument_id": transaction.instrument_id,
            "quantity": transaction.quantity,
            "price": transaction.price,
            "fee": transaction.fee,
            "tax": transaction.tax,
            "cash_impact": transaction.cash_impact,
            "transaction_id": transaction.id,
            "correlation_id": transaction.correlation_id,
            "checksum": transaction.checksum,
        }

    def _row_to_transaction(self, row: sqlite3.Row) -> Transaction:
        return Transaction(
            executed_at=row["executed_at"],
            asset_account_id=row["asset_account_id"],
            type=TransactionType(row["type"]),
            instrument_id=row["instrument_id"],
            quantity=row["quantity"],
            price=row["price"],
            fee=row["fee"],
            tax=row["tax"],
            cash_impact=row["cash_impact"],
            id=row["transaction_id"],
            correlation_id=row["correlation_id"],
            _checksum=row["checksum"],
        )
