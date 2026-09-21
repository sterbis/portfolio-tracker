from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal

from filterutils import Filter, FilterNode, Operator

from portfolio_tracker.application.persistence import MarketDataRepository
from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.domain.market_data import StockSplits
from portfolio_tracker.infrastructure.persistence.sqlite.executor import (
    Row,
    SqliteExecutor,
)
from portfolio_tracker.infrastructure.persistence.sqlite.registry import FieldReference


class SqliteMarketDataRepository(MarketDataRepository):
    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def ensure_stock_splits(self, splits: StockSplits) -> None:
        for executed_at, ratio in splits.splits.items():
            self._executor.insert_on_conflict_do_nothing(
                model=StockSplits,
                values={
                    "instrument_id": splits.instrument_id,
                    "executed_at": executed_at,
                    "ratio": ratio,
                },
                conflict_field_names=["instrument_id", "executed_at"],
            )

    def get_stock_splits(
        self,
        *,
        filter_: Filter | None = None,
    ) -> Iterator[StockSplits]:
        fields = [
            FieldReference(StockSplits, "instrument_id"),
            FieldReference(StockSplits, "executed_at"),
            FieldReference(StockSplits, "ratio"),
        ]

        rows = self._executor.select(
            model=StockSplits,
            fields=fields,
            filter_=filter_,
            sorts=[
                Sort("instrument_id", StockSplits),
                Sort("executed_at", StockSplits),
            ],
        )
        return self._rows_to_splits(rows)

    def get_stock_splits_by_instrument_ids(
        self, instrument_ids: set[str]
    ) -> list[StockSplits]:
        if not instrument_ids:
            return []

        return list(
            self.get_stock_splits(
                filter_=FilterNode(
                    "instrument_id", Operator.IN, instrument_ids, StockSplits
                ),
            )
        )

    def _rows_to_splits(self, rows: list[Row]) -> Iterator[StockSplits]:
        fields = [
            FieldReference(StockSplits, "instrument_id"),
            FieldReference(StockSplits, "executed_at"),
            FieldReference(StockSplits, "ratio"),
        ]

        current_instrument_id = None
        accumulated_splits: dict[datetime, Decimal] = {}

        for row in rows:
            instrument_id, executed_at, ratio = row.unpack(*fields)

            if (
                current_instrument_id is not None
                and instrument_id != current_instrument_id
            ):
                yield StockSplits(instrument_id, accumulated_splits)

                accumulated_splits = {}

            current_instrument_id = instrument_id
            accumulated_splits[executed_at] = ratio

        if current_instrument_id:
            yield StockSplits(current_instrument_id, accumulated_splits)
