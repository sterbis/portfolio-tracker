import sqlite3
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

from filterutils import Filter, FilterNode, Operator

from portfolio_tracker.application.ports.repositories import FxRatesRepository
from portfolio_tracker.domain.market_data import FxRates

from ..executor import SqliteExecutor


class SqliteFxRatesRepository(FxRatesRepository):
    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def ensure(self, rates: FxRates) -> None:
        for quote_currency, rate in rates.base_rates.items():
            self._executor.insert_on_conflict(
                table="fx_rate",
                values={
                    "effective_on": rates.effective_on,
                    "base_currency": rates.base_currency,
                    "quote_currency": quote_currency,
                    "rate": rate,
                },
                conflict_columns=["effective_on", "base_currency", "quote_currency"],
            )

    def get(
        self,
        *,
        filter_: Filter,
    ) -> Iterator[FxRates]:
        rows = self._executor.select(
            table="fx_rate",
            filter_=filter_,
            order_by=[("effective_on", "ASC"), ("base_currency", "ASC")],
        )
        return self._rows_to_rates(rows)

    def get_by_date(self, effective_on: date) -> FxRates | None:
        return next(
            self.get(filter_=FilterNode("effective_on", Operator.EQ, effective_on)),
            None,
        )

    def get_by_dates(self, dates: set[date]) -> list[FxRates]:
        return list(self.get(filter_=FilterNode("effective_on", Operator.IN, dates)))

    def get_latest(self) -> FxRates | None:
        row = self._executor.select_one(
            table="fx_rates",
            columns=["effective_on"],
            order_by=[("effective_on", "DESC")],
            limit=1,
        )
        if not row:
            return None

        return self.get_by_date(row["effective_on"])

    def get_distinct_dates(self) -> set[date]:
        rows = self._executor.select(
            table="fx_rates",
            columns=["effective_on"],
            distinct=True,
        )
        return {datetime.fromisoformat(row["effective_on"]).date() for row in rows}

    def _rows_to_rates(self, rows: list[sqlite3.Row]) -> Iterator[FxRates]:
        current_date = None
        current_base_currency = None
        accumulated_rates: dict[str, Decimal] = {}

        for row in rows:
            effective_on = date.fromisoformat(row["effective_on"])
            base_currency = row["base_currency"]

            if current_date is not None and (
                effective_on != current_date or base_currency != current_base_currency
            ):
                yield FxRates(effective_on, base_currency, accumulated_rates)

                accumulated_rates = {}

            current_date = effective_on
            current_base_currency = base_currency
            accumulated_rates[row["quote_currency"]] = Decimal(row["rate"])

        if current_date and current_base_currency:
            yield FxRates(current_date, current_base_currency, accumulated_rates)
