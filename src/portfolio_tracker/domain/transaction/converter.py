from datetime import date
from typing import Iterable, Iterator

from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.shared import DualMoney

from .models import ConvertedTransaction, Transaction


class TransactionConverter:
    def __init__(self, rates_by_date: dict[date, FxRates]) -> None:
        self._rates_by_date = rates_by_date

    def convert(
        self, transaction: Transaction, reporting_currency: str
    ) -> ConvertedTransaction:
        rates = self._rates_by_date[transaction.executed_at.date()]

        return ConvertedTransaction(
            id=transaction.id,
            correlation_id=transaction.correlation_id,
            checksum=transaction.checksum,
            asset_account_id=transaction.asset_account_id,
            executed_at=transaction.executed_at,
            type=transaction.type,
            instrument_id=transaction.instrument_id,
            quantity=transaction.quantity,
            price=DualMoney(
                native=transaction.price,
                reporting=transaction.price.convert(reporting_currency, rates),
            ),
            fee=DualMoney(
                native=transaction.fee,
                reporting=transaction.fee.convert(reporting_currency, rates),
            ),
            tax=DualMoney(
                native=transaction.tax,
                reporting=transaction.tax.convert(reporting_currency, rates),
            ),
            cash_impact=DualMoney(
                native=transaction.cash_impact,
                reporting=transaction.cash_impact.convert(reporting_currency, rates),
            ),
        )

    def convert_many(
        self, transactions: Iterable[Transaction], reporting_currency: str
    ) -> Iterator[ConvertedTransaction]:
        for transaction in transactions:
            yield self.convert(transaction, reporting_currency)
