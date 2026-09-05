from dataclasses import dataclass

from portfolio_tracker.domain.shared import Currency, Money


@dataclass(frozen=True)
class CashBalance:
    currencies: dict[Currency, Money]

    def __add__(self, other: CashBalance) -> CashBalance:
        if not isinstance(other, CashBalance):
            return NotImplemented

        return CashBalance(
            currencies={
                currency: self.currencies.get(currency, Money.zero(currency))
                + other.currencies.get(currency, Money.zero(currency))
                for currency in self.currencies.keys() | other.currencies.keys()
            },
        )


@dataclass(frozen=True)
class CashBalanceValuation:
    total_balance: Money


@dataclass(frozen=True)
class ValuedCashBalance:
    balance: CashBalance
    valuation: CashBalanceValuation
