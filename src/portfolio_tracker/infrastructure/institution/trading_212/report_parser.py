import csv
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from portfolio_tracker.application.institution import (
    InstitutionReportParser,
    InstitutionReportParserError,
    ReportInstrument,
    ReportTransaction,
)
from portfolio_tracker.domain.instrument import InstrumentType
from portfolio_tracker.domain.shared import Money
from portfolio_tracker.domain.transaction import TransactionType


@dataclass
class TransactionDetails:
    type: TransactionType
    instrument: ReportInstrument | None
    quantity: Decimal
    price: Money
    fee: Money
    tax: Money
    cash_impact: Money
    correlation_id: str | None = None


class Trading212ReportParser(InstitutionReportParser):
    _transaction_type_by_action = {
        "Currency conversion": TransactionType.CURRENCY_EXCHANGE,
        "Deposit": TransactionType.DEPOSIT,
        "Dividend (Dividend)": TransactionType.DIVIDEND,
        "Interest on cash": TransactionType.INTEREST,
        "Market buy": TransactionType.BUY,
        "Market sell": TransactionType.SELL,
        "Withdrawal": TransactionType.WITHDRAWAL,
    }

    def __init__(self, institution_account_id: str) -> None:
        super().__init__(institution_account_id)
        self._action_parsers: dict[
            str, Callable[[dict[str, Any]], list[TransactionDetails]]
        ] = {
            "Currency conversion": self._parse_currency_conversion_action,
            "Deposit": self._parse_cash_movement_action,
            "Dividend (Dividend)": self._parse_dividend_action,
            "Interest on cash": self._parse_cash_movement_action,
            "Market buy": self._parse_trade_action,
            "Market sell": self._parse_trade_action,
            "Withdrawal": self._parse_cash_movement_action,
        }

    @property
    def _external_account_id(self) -> str:
        return self._institution_account_id

    def parse_report(self, report: Iterator[str]) -> Iterator[ReportTransaction]:
        reader = csv.DictReader(report)

        for row in reader:
            action = row["Action"]
            parser = self._action_parsers.get(action)
            if parser is None:
                raise InstitutionReportParserError(
                    f"Unsupported report action: {action}."
                )

            for details in parser(row):
                yield ReportTransaction(
                    external_asset_account_id=self._external_account_id,
                    external_transaction_id=row["ID"],
                    executed_at=self._parse_datetime(row),
                    type=details.type,
                    instrument=details.instrument,
                    quantity=details.quantity,
                    price=details.price,
                    fee=details.fee,
                    tax=details.tax,
                    cash_impact=details.cash_impact,
                    correlation_id=details.correlation_id,
                )

    def _add_currency_conversion_details(
        self,
        row: dict[str, Any],
        details_list: list[TransactionDetails],
        *,
        rate: Decimal,
        from_amount: Decimal,
        from_currency: str,
        to_currency: str,
        expected_to_amount: Decimal | None = None,
    ) -> None:
        correlation_id = self._generate_correlation_id()
        for details in details_list:
            details.correlation_id = correlation_id

        details_list.extend(
            self._parse_currency_conversion(
                row=row,
                from_amount=from_amount,
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                expected_to_amount=expected_to_amount,
                correlation_id=correlation_id,
            )
        )

    def _parse_trade_action(self, row: dict[str, Any]) -> list[TransactionDetails]:
        details_list: list[TransactionDetails] = []

        transaction_type = self._parse_transaction_type(row)
        quantity = self._parse_quantity(row)
        price = self._parse_price(row)
        direction = self._get_cash_impact_direction(transaction_type)
        cash_impact = direction * quantity * price
        rate = self._parse_exchange_rate(row)

        trade_details = TransactionDetails(
            type=transaction_type,
            instrument=self._parse_instrument(row),
            quantity=quantity,
            price=price,
            fee=Money.zero(price.currency),
            tax=Money.zero(price.currency),
            cash_impact=cash_impact,
        )
        details_list.append(trade_details)

        if rate != Decimal("1.0"):
            total = self._parse_total(row)

            if transaction_type == TransactionType.BUY:
                from_amount = total.amount
                from_currency = total.currency
                expected_to_amount = trade_details.cash_impact.amount * -1
                to_currency = trade_details.cash_impact.currency

            else:
                from_amount = trade_details.cash_impact.amount
                from_currency = trade_details.cash_impact.currency
                expected_to_amount = total.amount
                to_currency = total.currency

            self._add_currency_conversion_details(
                row,
                details_list,
                rate=rate,
                from_amount=from_amount,
                from_currency=from_currency,
                to_currency=to_currency,
                expected_to_amount=expected_to_amount,
            )

        return details_list

    def _parse_currency_conversion_action(
        self, row: dict[str, Any]
    ) -> list[TransactionDetails]:
        from_amount = self._parse_currency_conversion_from_amount(row)
        to_amount = self._parse_currency_conversion_to_amount(row)

        if row.get("Exchange rate"):
            rate = self._parse_exchange_rate(row)
        else:
            rate = to_amount.amount / from_amount.amount

        return list(
            self._parse_currency_conversion(
                row, from_amount.amount, from_amount.currency, to_amount.currency, rate
            )
        )

    def _parse_dividend_action(self, row: dict[str, Any]) -> list[TransactionDetails]:
        details_list: list[TransactionDetails] = []

        quantity = self._parse_quantity(row)
        total = self._parse_total(row)
        rate = self._parse_exchange_rate(row)
        tax = self._parse_withholding_tax(row)
        cash_impact = Money(
            amount=(total.amount / rate),
            currency=tax.currency,
        )
        dividend_per_share = (cash_impact.amount + tax.amount) / quantity
        price = Money(amount=dividend_per_share, currency=cash_impact.currency)

        dividend_details = TransactionDetails(
            type=TransactionType.DIVIDEND,
            instrument=self._parse_instrument(row),
            quantity=quantity,
            price=price,
            fee=Money.zero(price.currency),
            tax=tax,
            cash_impact=cash_impact,
        )
        details_list.append(dividend_details)

        if rate != Decimal("1.0"):
            self._add_currency_conversion_details(
                row,
                details_list,
                rate=rate,
                from_amount=cash_impact.amount,
                from_currency=cash_impact.currency,
                to_currency=total.currency,
                expected_to_amount=total.amount,
            )

        return details_list

    def _parse_cash_movement_action(
        self, row: dict[str, Any]
    ) -> list[TransactionDetails]:
        transaction_type = self._parse_transaction_type(row)
        direction = self._get_cash_impact_direction(transaction_type)
        total = self._parse_total(row)
        cash_impact = direction * total
        return [
            TransactionDetails(
                type=transaction_type,
                instrument=None,
                quantity=Decimal("0.0"),
                price=Money.zero(cash_impact.currency),
                fee=Money.zero(cash_impact.currency),
                tax=Money.zero(cash_impact.currency),
                cash_impact=cash_impact,
            )
        ]

    def _parse_currency_conversion(
        self,
        row: dict[str, Any],
        from_amount: Decimal,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
        expected_to_amount: Decimal | None = None,
        correlation_id: str | None = None,
    ) -> tuple[TransactionDetails, TransactionDetails]:
        fee = (
            self._parse_currency_conversion_fee(row)
            if row.get("Currency conversion fee")
            else Money.zero(from_currency)
        )

        if fee.currency == from_currency:
            to_amount = (from_amount - fee.amount) * rate
        elif fee.currency == to_currency:
            to_amount = (from_amount * rate) - fee.amount
        else:
            raise InstitutionReportParserError(
                f"Unexpected {from_currency} -> {to_currency} "
                f"currency exchange fee currency: {fee.currency}."
            )

        if expected_to_amount and abs(to_amount - expected_to_amount) > Decimal(
            "0.001"
        ):
            raise InstitutionReportParserError(
                "Incorrect currency exchange fee application."
            )

        currency_sell_details = TransactionDetails(
            type=TransactionType.CURRENCY_EXCHANGE,
            instrument=None,
            quantity=from_amount,
            price=Money(amount=rate, currency=to_currency),
            fee=fee if fee.currency == from_currency else Money.zero(from_currency),
            tax=Money.zero(from_currency),
            cash_impact=Money(amount=(-1 * from_amount), currency=from_currency),
            correlation_id=correlation_id,
        )

        currency_buy_details = TransactionDetails(
            type=TransactionType.CURRENCY_EXCHANGE,
            instrument=None,
            quantity=to_amount,
            price=Money(amount=(Decimal("1.0") / rate), currency=from_currency),
            fee=fee if fee.currency == to_currency else Money.zero(to_currency),
            tax=Money.zero(to_currency),
            cash_impact=Money(amount=to_amount, currency=to_currency),
            correlation_id=correlation_id,
        )
        return currency_sell_details, currency_buy_details

    def _parse_instrument(self, row: dict[str, Any]) -> ReportInstrument:
        return ReportInstrument(
            type=InstrumentType.STOCK,
            name=row["Name"],
            symbol=row["Ticker"],
            currency=row["Currency (Price / share)"],
            details={"isin": row["ISIN"]},
        )

    def _parse_transaction_type(self, row: dict[str, Any]) -> TransactionType:
        try:
            return self._transaction_type_by_action[row["Action"]]
        except KeyError as error:
            raise InstitutionReportParserError(
                f"Unsupported report action: {row['Action']}."
            ) from error

    def _parse_datetime(self, row: dict[str, Any]) -> datetime:
        return datetime.fromisoformat(row["Time"]).replace(tzinfo=timezone.utc)

    def _parse_quantity(self, row: dict[str, Any]) -> Decimal:
        return self._to_abs_decimal(row["No. of shares"])

    def _parse_exchange_rate(self, row: dict[str, Any]) -> Decimal:
        return self._to_decimal(row["Exchange rate"])

    def _parse_price(self, row: dict[str, Any]) -> Money:
        return Money(
            amount=self._to_abs_decimal(row["Price / share"]),
            currency=row["Currency (Price / share)"],
        )

    def _parse_total(self, row: dict[str, Any]) -> Money:
        return Money(
            amount=self._to_abs_decimal(row["Total"]),
            currency=row["Currency (Total)"],
        )

    def _parse_withholding_tax(self, row: dict[str, Any]) -> Money:
        return Money(
            amount=self._to_decimal(row["Withholding tax"]),
            currency=row["Currency (Withholding tax)"],
        )

    def _parse_currency_conversion_from_amount(self, row: dict[str, Any]) -> Money:
        return Money(
            amount=self._to_decimal(row["Currency conversion from amount"]),
            currency=row["Currency (Currency conversion from amount)"],
        )

    def _parse_currency_conversion_to_amount(self, row: dict[str, Any]) -> Money:
        return Money(
            amount=self._to_decimal(row["Currency conversion to amount"]),
            currency=row["Currency (Currency conversion to amount)"],
        )

    def _parse_currency_conversion_fee(self, row: dict[str, Any]) -> Money:
        return Money(
            amount=self._to_abs_decimal(row["Currency conversion fee"]),
            currency=row["Currency (Currency conversion fee)"],
        )
