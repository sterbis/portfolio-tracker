from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from enum import Enum

from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.shared import DualMoney, Money
from portfolio_tracker.domain.transaction import Transaction, TransactionType

from .models import Position, TaxLot


class AccountingMethod(Enum):
    AVERAGE_COST = "AVERAGE_COST"
    FIFO = "FIFO"


class PositionBuilder:
    def __init__(
        self,
        instrument_id: str,
        native_currency: str,
        reporting_currency: str,
        accounting_method: AccountingMethod = AccountingMethod.FIFO,
    ) -> None:
        self.instrument_id = instrument_id
        self.native_currency = native_currency
        self.reporting_currency = reporting_currency
        self.accounting_method = accounting_method
        self._lots: list[TaxLot] = []

        self._opened_at: datetime | None = None
        self._last_trade_at: datetime | None = None
        self._last_trade_type: str = ""
        self._last_buy_at: datetime | None = None
        self._closed_at: datetime | None = None

    @property
    def quantity(self) -> Decimal:
        return sum((lot.remaining_quantity for lot in self._lots), Decimal("0"))

    @property
    def fees(self) -> DualMoney:
        return sum(
            (lot.fee for lot in self._lots),
            DualMoney.zero(self.native_currency, self.reporting_currency),
        )

    @property
    def cost_basis(self) -> DualMoney:
        return sum(
            (lot.cost_basis for lot in self._lots),
            DualMoney.zero(self.native_currency, self.reporting_currency),
        )

    @property
    def average_price(self) -> DualMoney:
        if self.quantity == 0:
            return DualMoney.zero(self.native_currency, self.reporting_currency)
        return self.cost_basis / self.quantity

    @property
    def lots(self) -> list[TaxLot]:
        return self._lots

    def add(self, transaction: Transaction, rates: FxRates) -> None:
        if not transaction.instrument_id:
            raise ValueError("Missing transaction instrument.")
        if transaction.instrument_id != self.instrument_id:
            raise ValueError(
                "Invalid transaction instrument. "
                f"Expected '{self.instrument_id}', got '{transaction.instrument_id}'."
            )
        if self._last_trade_at and self._last_trade_at > transaction.executed_at:
            raise ValueError("Tracked transactions must be sorted by datetime.")

        if not self._opened_at:
            self._opened_at = transaction.executed_at

        self._last_trade_at = transaction.executed_at
        self._last_trade_type = transaction.type.value

        if transaction.type == TransactionType.BUY:
            self._last_buy_at = transaction.executed_at
            self._closed_at = None
            self._process_buy(transaction, rates)

        elif transaction.type == TransactionType.SELL:
            self._process_sell(transaction)
            if self.quantity == 0:
                self._closed_at = transaction.executed_at

        else:
            raise ValueError(
                f"Invalid transaction type: {transaction.type}. "
                f"Only {TransactionType.BUY} and {TransactionType.SELL} transactions allowed."
            )

    def _process_buy(self, transaction: Transaction, rates: FxRates) -> None:
        price_reporting_rate = rates.get_rate(
            transaction.price.currency, self.reporting_currency
        )
        fee_native_rate = rates.get_rate(
            transaction.fee.currency, transaction.price.currency
        )
        fee_reporting_rate = rates.get_rate(
            transaction.fee.currency, self.reporting_currency
        )

        lot = TaxLot(
            transaction_id=transaction.id,
            executed_at=transaction.executed_at,
            original_quantity=transaction.quantity,
            remaining_quantity=transaction.quantity,
            price=DualMoney(
                native=transaction.price,
                reporting=Money(
                    transaction.price.amount * price_reporting_rate,
                    self.reporting_currency,
                ),
            ),
            fee=DualMoney(
                native=Money(
                    transaction.fee.amount * fee_native_rate, self.native_currency
                ),
                reporting=Money(
                    transaction.fee.amount * fee_reporting_rate, self.reporting_currency
                ),
            ),
        )
        self._lots.append(lot)

    def _process_sell(self, transaction: Transaction) -> None:
        if transaction.quantity > self.quantity:
            raise ValueError(
                f"Short selling protection: Selling {transaction.quantity} but only holding {self.quantity}"
            )

        if self.accounting_method == AccountingMethod.FIFO:
            self._execute_fifo_sell(transaction.quantity)
        elif self.accounting_method == AccountingMethod.AVERAGE_COST:
            self._execute_average_cost_sell(transaction.quantity)

    def _execute_fifo_sell(self, quantity: Decimal) -> None:
        remaining_quantity = quantity
        updated_lots = []

        for lot in self._lots:
            if remaining_quantity <= 0:
                updated_lots.append(lot)
                continue

            if remaining_quantity >= lot.remaining_quantity:
                remaining_quantity -= lot.remaining_quantity
            else:
                updated_remaining_quantity = lot.remaining_quantity - remaining_quantity
                ratio = updated_remaining_quantity / lot.remaining_quantity
                updated_fee = lot.fee * ratio

                updated_lots.append(
                    replace(
                        lot,
                        remaining_quantity=updated_remaining_quantity,
                        fee=updated_fee,
                    )
                )
                remaining_quantity = Decimal("0")

        self._lots = updated_lots

    def _execute_average_cost_sell(self, quantity: Decimal) -> None:
        average_price = self.average_price

        remaining_quantity = quantity
        updated_lots = []

        for lot in self._lots:
            if remaining_quantity <= 0:
                updated_lots.append(
                    replace(
                        lot,
                        price=average_price,
                        fee=lot.fee.to_zero(),
                    )
                )
                continue

            if remaining_quantity >= lot.remaining_quantity:
                remaining_quantity -= lot.remaining_quantity

            else:
                updated_remaining_quantity = lot.remaining_quantity - remaining_quantity
                updated_lots.append(
                    replace(
                        lot,
                        remaining_quantity=updated_remaining_quantity,
                        price=average_price,
                        fee=lot.fee.to_zero(),
                    )
                )
                remaining_quantity = Decimal("0")

        self._lots = updated_lots

    def get_position_snapshot(self) -> Position:
        return Position(
            instrument_id=self.instrument_id,
            quantity=self.quantity,
            cost_basis=self.cost_basis,
            fees=self.fees,
            opened_at=self._opened_at or datetime.now(),
            last_trade_at=self._last_trade_at or datetime.now(),
            last_trade_type=self._last_trade_type,
            last_buy_at=self._last_buy_at,
            closed_at=self._closed_at,
            is_tax_free=False,  # Will be evaluated by Legislation/Config Engine
            _tax_free_position=None,  # Will be evaluated by Legislation/Config Engine
        )
