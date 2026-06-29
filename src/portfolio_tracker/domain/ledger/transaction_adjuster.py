from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from portfolio_tracker.domain.market_data import StockSplits

from .transaction import Transaction, TransactionType


class TransactionAdjuster:
    def adjust(
        self,
        transactions: Iterable[Transaction],
        splits_list: list[StockSplits],
        snapshot_at: datetime | None = None,
    ) -> Iterable[Transaction]:
        splits_by_instrument_id = {
            splits.instrument_id: splits for splits in splits_list
        }
        snapshot_at = snapshot_at or datetime.now(timezone.utc)

        for transaction in transactions:
            adjusted_transaction = transaction

            if transaction.type in (TransactionType.BUY, TransactionType.SELL):
                assert transaction.instrument_id is not None
                if splits := splits_by_instrument_id.get(transaction.instrument_id):
                    adjusted_transaction = self._adjust_for_stock_splits(
                        transaction, splits, snapshot_at
                    )

            yield adjusted_transaction

    def _adjust_for_stock_splits(
        self,
        transaction: Transaction,
        splits: StockSplits,
        snapshot_at: datetime,
    ) -> Transaction:
        multiplier = splits.get_multiplier(transaction.executed_at, snapshot_at)
        if multiplier == Decimal("1.0"):
            return transaction

        return replace(
            transaction,
            _id=None,
            quantity=transaction.quantity * multiplier,
            price=transaction.price / multiplier,
        )
