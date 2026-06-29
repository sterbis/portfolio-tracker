from portfolio_tracker.domain.ledger import Transaction
from portfolio_tracker.domain.shared import Money

from .models import CashBalance


class CashBalanceBuilder:
    def __init__(self) -> None:
        self._currencies: dict[str, Money] = {}

    def add(self, transaction: Transaction) -> None:
        currency = transaction.cash_impact.currency
        if currency not in self._currencies:
            self._currencies[currency] = transaction.cash_impact

        else:
            self._currencies[currency] += transaction.cash_impact

    def get_cash_balance_snapshot(self) -> CashBalance:
        return CashBalance(currencies=self._currencies)
