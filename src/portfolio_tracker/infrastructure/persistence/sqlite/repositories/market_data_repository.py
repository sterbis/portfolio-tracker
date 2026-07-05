import sqlite3
from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal

from filterutils import Filter, FilterNode, Operator

from portfolio_tracker.application.ports.repositories import MarketDataRepository
from portfolio_tracker.domain.market_data import StockSplits

from ..executor import SqliteExecutor


class SqliteMarketDataRepository(MarketDataRepository):
    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def ensure_stock_splits(self, splits: StockSplits) -> None:
        for executed_at, ratio in splits.splits.items():
            self._executor.insert_if_not_exists(
                table="stock_split",
                values={
                    "instrument_id": splits.instrument_id,
                    "executed_at": executed_at,
                    "ratio": ratio,
                },
                conflict_columns=["instrument_id", "executed_at"],
            )

    def get_stock_splits(
        self,
        *,
        filter_: Filter | None = None,
    ) -> Iterator[StockSplits]:
        rows = self._executor.select(
            table="stock_split",
            filter_=filter_,
            order_by=[("instrument_id", "ASC"), ("executed_at", "ASC")],
        )
        return self._rows_to_splits(rows)

    def get_stock_splits_by_instrument_ids(
        self, instrument_ids: set[str]
    ) -> list[StockSplits]:
        if not instrument_ids:
            return []

        return list(
            self.get_stock_splits(
                filter_=FilterNode("instrument_id", Operator.IN, instrument_ids),
            )
        )

    def _rows_to_splits(self, rows: list[sqlite3.Row]) -> Iterator[StockSplits]:
        current_instrument_id = None
        accumulated_splits: dict[datetime, Decimal] = {}

        for row in rows:
            instrument_id = row["instrument_id"]

            if (
                current_instrument_id is not None
                and instrument_id != current_instrument_id
            ):
                yield StockSplits(instrument_id, accumulated_splits)

                accumulated_splits = {}

            current_instrument_id = instrument_id
            executed_at = row["executed_at"]
            accumulated_splits[executed_at] = row["ratio"]

        if current_instrument_id:
            yield StockSplits(current_instrument_id, accumulated_splits)
