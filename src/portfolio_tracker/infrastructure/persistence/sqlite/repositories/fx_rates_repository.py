from collections.abc import Iterator
from datetime import date
from decimal import Decimal

from filterutils import Filter, FilterNode, Operator

from portfolio_tracker.application.persistence import FxRatesRepository, OrderBy
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.infrastructure.persistence.sqlite.executor import SqliteExecutor
from portfolio_tracker.infrastructure.persistence.sqlite.registry import FieldReference


class SqliteFxRatesRepository(FxRatesRepository):
    def __init__(self, executor: SqliteExecutor) -> None:
        self._executor = executor

    def ensure(self, rates: FxRates) -> None:
        for quote_currency, rate in rates.base_rates.items():
            self._executor.insert_on_conflict_do_nothing(
                entity=FxRates,
                values={
                    "effective_on": rates.effective_on,
                    "base_currency": rates.base_currency,
                    "quote_currency": quote_currency,
                    "rate": rate,
                },
                conflict_field_names=["effective_on", "base_currency", "quote_currency"],
            )

    def get(
        self,
        *,
        filter_: Filter | None = None,
    ) -> Iterator[FxRates]:
        references = [
            FieldReference("effective_on", FxRates),
            FieldReference("base_currency", FxRates),
            FieldReference("quote_currency", FxRates),
            FieldReference("rate", FxRates)
        ]
        
        rows = self._executor.select(
            entity=FxRates,
            fields=references,
            filter_=filter_,
            order_by_list=[
                OrderBy("effective_on", FxRates, "ASC"),
                OrderBy("base_currency", FxRates, "ASC"),
            ],
        )
        
        current_date = None
        current_base_currency = None
        accumulated_rates: dict[str, Decimal] = {}
        
        for row in rows:
            effective_on, base_currency, quote_currency, rate = row.unpack(*references)
        
            if current_date is not None and (
                effective_on != current_date or base_currency != current_base_currency
            ):
                yield FxRates(effective_on, base_currency, accumulated_rates)
        
                accumulated_rates = {}
        
            current_date = effective_on
            current_base_currency = base_currency
            accumulated_rates[quote_currency] = rate
        
        if current_date and current_base_currency:
            yield FxRates(current_date, current_base_currency, accumulated_rates)

    def get_by_date(self, effective_on: date) -> FxRates | None:
        return next(
            self.get(filter_=FilterNode("effective_on", Operator.EQ, effective_on, FxRates)),
            None,
        )

    def get_by_dates(self, dates: set[date]) -> list[FxRates]:
        if not dates:
            return []

        return list(self.get(filter_=FilterNode("effective_on", Operator.IN, dates, FxRates)))

    def get_latest(self) -> FxRates | None:
        effective_on_ref = FieldReference("effective_on", FxRates)

        row = self._executor.select_one(
            entity=FxRates,
            fields=[effective_on_ref],
            order_by_list=[OrderBy("effective_on", FxRates, "DESC")],
        )
        if not row:
            return None

        return self.get_by_date(row[effective_on_ref])

    def get_distinct_dates(self) -> set[date]:
        effective_on_ref = FieldReference("effective_on", FxRates)
    
        rows = self._executor.select(
            entity=FxRates,
            fields=[effective_on_ref],
            distinct=True,
        )
        return {row[effective_on_ref].date() for row in rows}
