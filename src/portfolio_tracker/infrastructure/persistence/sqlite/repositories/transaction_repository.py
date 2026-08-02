import sqlite3
from datetime import date
from typing import Any

from filterutils import ColumnMap, Filter, FilterNode, FilterTree, Operator

from portfolio_tracker.application.persistence import OrderBy, TransactionRepository
from portfolio_tracker.domain.instrument import Instrument
from portfolio_tracker.domain.transaction import Transaction, TransactionType
from portfolio_tracker.infrastructure.persistence.sqlite.executor import SqliteExecutor


class SqliteTransactionRepository(TransactionRepository):
    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def add(self, transaction: Transaction) -> None:
        self._executor.insert(
            table="ledger",
            values=self._transaction_to_values(transaction),
        )

    def ensure(self, transaction: Transaction) -> None:
        self._executor.insert_on_conflict_do_nothing(
            entity_reference="ledger",
            values=self._transaction_to_values(transaction),
            conflict_fields=["checksum"],
        )

    def get(
        self,
        *,
        filter_: Filter | None = None,
        order_by: list[OrderBy] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Transaction]:
        alias = None
        columns: list[str] = []
        joins: list[Join] = []
        column_map: ColumnMap = {}
    
        if filter_ and isinstance(filter_, FilterTree):
            for item_type in filter_.item_types:
                if item_type == Instrument:
                    joins.append(
                        Join(
                            table="instrument",
                            left_column="t.instrument_id",
                            right_column="i.instrument_id",
                            alias="i",
                        )
                    )
                    column_map.update(generate_column_map(item_type, "i"))

            if column_map:
                alias = "t"
                columns = ["t.*"]
                column_map.update(generate_column_map(Transaction, alias))

        rows = self._executor.select(
            table="ledger",
            alias=alias,
            columns=columns,
            joins=joins,
            filter_=filter_,
            order_by=order_by,
            limit=limit,
            offset=offset,
            column_map=column_map,
        )
        return [self._row_to_transaction(row, column_map) for row in rows]

    def get_by_id(self, transaction_id: str) -> Transaction | None:
        row = self._executor.select_one(
            table="ledger",
            filter_=FilterNode("transaction_id", Operator.EQ, transaction_id),
        )
        return self._row_to_transaction(row) if row else None

    def get_distinct_dates(self, filter_: Filter | None = None) -> set[date]:
        rows = self._executor.select(
            table="ledger",
            columns=["executed_at"],
            distinct=True,
            filter_=filter_,
        )
        return {row["executed_at"].date() for row in rows}

    def get_distinct_instrument_ids(self, filter_: Filter | None = None) -> set[str]:
        rows = self._executor.select(
            table="ledger",
            columns=["instrument_id"],
            distinct=True,
            filter_=filter_,
        )
        return {row["instrument_id"] for row in rows}

    def update(self, transaction: Transaction) -> None:
        self._executor.update(
            entity_reference="ledger",
            values=self._transaction_to_values(transaction),
            filter_=FilterNode("transaction_id", Operator.EQ, transaction.id),
        )

    def remove(self, filter_: Filter) -> None:
        self._executor.delete(
            entity_reference="ledger",
            filter_=filter_,
        )

    def remove_by_id(self, transaction_id: str) -> None:
        self.remove(filter_=FilterNode("transaction_id", Operator.EQ, transaction_id))

    def remove_by_asset_account_id(self, account_id: str) -> None:
        self.remove(filter_=FilterNode("asset_account_id", Operator.EQ, account_id))

    def exists(self, filter_: Filter) -> bool:
        row = self._executor.select_one(
            table="ledger",
            columns=["1"],
            filter_=filter_,
            limit=1,
        )
        return row is not None

    def exists_by_checksum(self, checksum: str) -> bool:
        return self.exists(filter_=FilterNode("checksum", Operator.EQ, checksum))

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

    def _row_to_transaction(self, row: sqlite3.Row, column_map: ColumnMap | None = None) -> Transaction:
        column_map = column_map or {}

        def resolve_column(column: str) -> str:
            return column_map.get((Transaction, column), column)

        return Transaction(
            executed_at=row[resolve_column("executed_at")],
            asset_account_id=row[resolve_column("asset_account_id")],
            type=TransactionType(row[resolve_column("type")]),
            instrument_id=row[resolve_column("instrument_id")],
            quantity=row[resolve_column("quantity")],
            price=row[resolve_column("price")],
            fee=row[resolve_column("fee")],
            tax=row[resolve_column("tax")],
            cash_impact=row[resolve_column("cash_impact")],
            id=row[resolve_column("transaction_id")],
            correlation_id=row[resolve_column("correlation_id")],
            _checksum=row[resolve_column("checksum")],
        )
