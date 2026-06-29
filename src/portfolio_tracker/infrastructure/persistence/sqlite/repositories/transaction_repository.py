import sqlite3
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from filterutils import Filter, FilterNode, Operator

from portfolio_tracker.application.ports.repositories import TransactionRepository
from portfolio_tracker.domain.ledger import Transaction, TransactionType
from portfolio_tracker.domain.shared import Money

from ..executor import SqliteExecutor


class SqliteTransactionRepository(TransactionRepository):
    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def add(self, transaction: Transaction) -> None:
        self._executor.insert(
            table="transaction",
            values=self._transaction_to_values(transaction),
        )

    def ensure(self, transaction: Transaction) -> None:
        self._executor.insert_on_conflict(
            table="transaction",
            values=self._transaction_to_values(transaction),
            conflict_columns=["transaction_id"],
        )

    def get(
        self,
        *,
        filter_: Filter,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Transaction]:
        rows = self._executor.select(
            table="transaction",
            filter_=filter_,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_transaction(row) for row in rows]

    def get_by_id(self, transaction_id: str) -> Transaction | None:
        row = self._executor.select_one(
            table="transaction",
            filter_=FilterNode("transaction_id", Operator.EQ, transaction_id),
        )
        return self._row_to_transaction(row) if row else None

    def get_distinct_dates(self, filter_: Filter) -> set[date]:
        rows = self._executor.select(
            table="transaction",
            columns=["executed_at"],
            distinct=True,
            filter_=filter_,
        )
        return {datetime.fromisoformat(row["executed_at"]).date() for row in rows}

    def get_distinct_instrument_ids(self, filter_: Filter) -> set[str]:
        rows = self._executor.select(
            table="transaction",
            columns=["instrument_id"],
            distinct=True,
            filter_=filter_,
        )
        return {row["instrument_id"] for row in rows}

    def update(self, transaction: Transaction) -> None:
        self._executor.update(
            table="transaction",
            values=self._transaction_to_values(transaction),
            filter_=FilterNode("transaction_id", Operator.EQ, transaction.id),
        )

    def remove_by_id(self, transaction_id: str) -> None:
        self._executor.delete(
            table="transaction",
            filter_=FilterNode("transaction_id", Operator.EQ, transaction_id),
        )

    def exists_by_id(self, transaction_id: str) -> bool:
        row = self._executor.select_one(
            table="transaction",
            columns=["1"],
            filter_=FilterNode("transaction_id", Operator.EQ, transaction_id),
            limit=1,
        )
        return row is not None

    def _transaction_to_values(self, transaction: Transaction) -> dict[str, Any]:
        return {
            "transaction_id": transaction.id,
            "correlation_id": transaction.correlation_id,
            "executed_at": transaction.executed_at,
            "asset_account_id": transaction.asset_account_id,
            "type": transaction.type,
            "instrument_id": transaction.instrument_id,
            "quantity": transaction.quantity,
            "price_amount": transaction.price.amount,
            "price_currency": transaction.price.currency,
            "fee_amount": transaction.fee.amount,
            "fee_currency": transaction.fee.currency,
            "tax_amount": transaction.tax.amount,
            "tax_currency": transaction.tax.currency,
            "cash_impact_amount": transaction.cash_impact.amount,
            "cash_impact_currency": transaction.cash_impact.currency,
        }

    def _row_to_transaction(self, row: sqlite3.Row) -> Transaction:
        return Transaction(
            _id=row["transaction_id"],
            correlation_id=row["correlation_id"],
            executed_at=datetime.fromisoformat(row["executed_at"]),
            asset_account_id=row["asset_account_id"],
            type=TransactionType(row["type"]),
            instrument_id=row["instrument_id"],
            quantity=Decimal(row["quantity"]),
            price=Money(Decimal(row["price_amount"]), row["price_currency"]),
            fee=Money(Decimal(row["fee_amount"]), row["fee_currency"]),
            tax=Money(Decimal(row["tax_amount"]), row["tax_currency"]),
            cash_impact=Money(
                Decimal(row["cash_impact_amount"]), row["cash_impact_currency"]
            ),
        )
