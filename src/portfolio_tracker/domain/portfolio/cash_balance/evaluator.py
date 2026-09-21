from decimal import Decimal

from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.shared import Currency, Money

from .models import (
    CashBalance,
    CashBalanceValuation,
    ValuedCashBalance,
)


class CashBalanceEvaluator:
    def get_valuation(
        self, cash_balance: CashBalance, reporting_currency: Currency, rates: FxRates
    ) -> CashBalanceValuation:
        total_amount = Decimal("0.0")
        for currency, balance in cash_balance.currencies.items():
            rate = rates.get_rate(currency, reporting_currency)
            total_amount += balance.amount * rate

        return CashBalanceValuation(
            total_balance=Money(total_amount, reporting_currency)
        )

    def evaluate(
        self, cash_balance: CashBalance, reporting_currency: Currency, rates: FxRates
    ) -> ValuedCashBalance:
        return ValuedCashBalance(
            balance=cash_balance,
            valuation=self.get_valuation(cash_balance, reporting_currency, rates),
        )
