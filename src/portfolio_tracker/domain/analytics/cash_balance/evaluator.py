from decimal import Decimal

from portfolio_tracker.domain.market_data import FxRates
from portfolio_tracker.domain.shared import Money

from .models import (
    CashBalance,
    CashBalanceValuation,
)


class CashBalanceEvaluator:
    def evaluate(
        self, cash_balance: CashBalance, reporting_currency: str, rates: FxRates
    ) -> CashBalanceValuation:
        total_amount = Decimal("0.0")
        for currency, balance in cash_balance.currencies.items():
            rate = rates.get_rate(currency, reporting_currency)
            total_amount += balance.amount * rate

        return CashBalanceValuation(
            total_balance=Money(total_amount, reporting_currency)
        )
