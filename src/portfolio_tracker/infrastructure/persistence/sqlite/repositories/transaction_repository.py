from datetime import date
from typing import Any

from filterutils import Filter, FilterNode, Operator

from portfolio_tracker.application.persistence import TransactionRepository
from portfolio_tracker.application.shared.order_by import OrderBy
from portfolio_tracker.domain.transaction import Transaction, TransactionType
from portfolio_tracker.infrastructure.persistence.sqlite.executor import (
    Row,
    SqliteExecutor,
)
from portfolio_tracker.infrastructure.persistence.sqlite.registry import FieldReference


class SqliteTransactionRepository(TransactionRepository):
    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def add(self, transaction: Transaction) -> None:
        self._executor.insert(
            model=Transaction,
            values=self._transaction_to_values(transaction),
        )

    def ensure(self, transaction: Transaction) -> None:
        self._executor.insert_on_conflict_do_nothing(
            model=Transaction,
            values=self._transaction_to_values(transaction),
            conflict_field_names=["checksum"],
        )

    def get(
        self,
        *,
        filter_: Filter | None = None,
        order_by_list: list[OrderBy] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Transaction]:
        rows = self._executor.select(
            model=Transaction,
            filter_=filter_,
            order_by_list=order_by_list,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_transaction(row) for row in rows]

    def get_by_id(self, transaction_id: str) -> Transaction | None:
        row = self._executor.select_one(
            model=Transaction,
            filter_=FilterNode("id", Operator.EQ, transaction_id, Transaction),
        )
        return self._row_to_transaction(row) if row else None

    def get_distinct_dates(self, filter_: Filter | None = None) -> set[date]:
        executed_at_field = FieldReference(Transaction, "executed_at")
        rows = self._executor.select(
            model=Transaction,
            fields=[executed_at_field],
            distinct=True,
            filter_=filter_,
        )
        return {row[executed_at_field].date() for row in rows}

    def get_distinct_instrument_ids(self, filter_: Filter | None = None) -> set[str]:
        instrument_id_field = FieldReference(Transaction, "instrument_id")
        rows = self._executor.select(
            model=Transaction,
            fields=[instrument_id_field],
            distinct=True,
            filter_=filter_,
        )
        return {row[instrument_id_field] for row in rows}

    def update(self, transaction: Transaction) -> None:
        self._executor.update(
            model=Transaction,
            values=self._transaction_to_values(transaction),
            filter_=FilterNode("id", Operator.EQ, transaction.id, Transaction),
        )

    def remove(self, filter_: Filter) -> None:
        self._executor.delete(
            model=Transaction,
            filter_=filter_,
        )

    def remove_by_id(self, transaction_id: str) -> None:
        self.remove(filter_=FilterNode("id", Operator.EQ, transaction_id, Transaction))

    def remove_by_asset_account_id(self, account_id: str) -> None:
        self.remove(
            filter_=FilterNode("asset_account_id", Operator.EQ, account_id, Transaction)
        )

    def exists(self, filter_: Filter) -> bool:
        row = self._executor.select_one(
            model=Transaction,
            fields=[FieldReference(Transaction, "id")],
            filter_=filter_,
        )
        return row is not None

    def exists_by_checksum(self, checksum: str) -> bool:
        return self.exists(
            filter_=FilterNode("checksum", Operator.EQ, checksum, Transaction)
        )

    def _transaction_to_values(self, transaction: Transaction) -> dict[str, Any]:
        return {
            "id": transaction.id,
            "correlation_id": transaction.correlation_id,
            "checksum": transaction.checksum,
            "executed_at": transaction.executed_at,
            "asset_account_id": transaction.asset_account_id,
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
            id=row[field("id")],
            correlation_id=row[field("correlation_id")],
            provided_checksum=row[field("checksum")],
            executed_at=row[field("executed_at")],
            asset_account_id=row[field("asset_account_id")],
            type=TransactionType(row[field("type")]),
            instrument_id=row[field("instrument_id")],
            quantity=row[field("quantity")],
            price=row[field("price")],
            fee=row[field("fee")],
            tax=row[field("tax")],
            cash_impact=row[field("cash_impact")],
        )
