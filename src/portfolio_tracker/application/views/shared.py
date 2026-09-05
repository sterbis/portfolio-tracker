from dataclasses import dataclass
from decimal import Decimal

from portfolio_tracker.domain.shared import Currency, DualMoney, Money


@dataclass(frozen=True)
class MoneyView:
    amount: Decimal
    currency: Currency

    @classmethod
    def from_domain(cls, money: Money) -> MoneyView:
        return cls(amount=money.amount, currency=money.currency)


@dataclass(frozen=True)
class DualMoneyView:
    native: MoneyView
    reporting: MoneyView

    @classmethod
    def from_domain(cls, dual_money: DualMoney) -> DualMoneyView:
        return cls(
            native=MoneyView.from_domain(dual_money.native),
            reporting=MoneyView.from_domain(dual_money.reporting),
        )
