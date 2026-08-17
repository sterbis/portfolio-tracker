from portfolio_tracker.domain.shared import Money
from portfolio_tracker.domain.transaction import ConvertedTransaction

from .models import CashBalance


class CashBalanceBuilder:
    def __init__(self) -> None:
        self._currency_balances: dict[str, Money] = {}

    def add(self, transaction: ConvertedTransaction) -> None:
        currency = transaction.cash_impact.native.currency
        if currency not in self._currency_balances:
            self._currency_balances[currency] = transaction.cash_impact.native
        else:
            self._currency_balances[currency] += transaction.cash_impact.native

    def get_cash_balance_snapshot(self) -> CashBalance:
        return CashBalance(currencies=self._currency_balances)
