# pylint: disable=redefined-outer-name
# pylint: disable=protected-access

from decimal import Decimal
from typing import Any

import pytest

from portfolio_tracker.application.contracts.dtos import MoneyDto
from portfolio_tracker.infrastructure.institution.trading_212 import (
    Trading212ReportParser,
)


@pytest.fixture(scope="module")
def report_parser() -> Trading212ReportParser:
    return Trading212ReportParser("acct_001")


@pytest.fixture(scope="module")
def market_buy_row() -> dict[str, Any]:
    return {
        "Action": "Market buy",
        "No. of shares": 23.1921858000,
        "Price / share": 175.6700000000,
        "Currency (Price / share)": "USD",
        "Exchange rate": 1.06480041,
        "Total": 3831.97,
        "Currency (Total)": "EUR",
        "Currency conversion fee": 5.74,
        "Currency (Currency conversion fee)": "EUR",
    }


@pytest.fixture(scope="module")
def market_sell_row() -> dict[str, Any]:
    return {
        "Action": "Market sell",
        "No. of shares": 4.7140158000,
        "Price / share": 190.9200000000,
        "Currency (Price / share)": "USD",
        "Exchange rate": 1.00000000,
        "Total": 900.00,
        "Currency (Total)": "USD",
        "Currency conversion fee": None,
        "Currency (Currency conversion fee)": None,
    }


@pytest.fixture(scope="module")
def dividend_row() -> dict[str, Any]:
    return {
        "Action": "Dividend (Dividend)",
        "No. of shares": 25.0000000000,
        "Price / share": 0.425000,
        "Currency (Price / share)": "USD",
        "Exchange rate": 0.85600300,
        "Total": 9.10,
        "Currency (Total)": "EUR",
        "Withholding tax": 1.88,
        "Currency (Withholding tax)": "USD",
    }


@pytest.fixture(scope="module")
def currency_conversion_row() -> dict[str, Any]:
    return {
        "Action": "Currency conversion",
        "Currency conversion from amount": 4612.31,
        "Currency (Currency conversion from amount)": "USD",
        "Currency conversion to amount": 110165.25,
        "Currency (Currency conversion to amount)": "CZK",
        "Currency conversion fee": -165.25,
        "Currency (Currency conversion fee)": "CZK",
    }


@pytest.mark.parametrize(
    (
        "row_fixture, from_amount, from_currency, to_currency, rate, "
        "expected_to_amount, expected_sell_fee, expected_buy_fee"
    ),
    [
        (
            "market_buy_row",
            Decimal("3831.97"),
            "EUR",
            "USD",
            Decimal("1.06480041"),
            (Decimal("23.1921858000") * Decimal("175.6700000000")),
            MoneyDto(amount=Decimal("5.74"), currency="EUR"),
            MoneyDto(amount=Decimal("0.0"), currency="USD"),
        ),
        (
            "market_sell_row",
            (Decimal("4.7140158000") * Decimal("190.9200000000")),
            "USD",
            "USD",
            Decimal("1.00000000"),
            Decimal("900.00"),
            MoneyDto(amount=Decimal("0.0"), currency="USD"),
            MoneyDto(amount=Decimal("0.0"), currency="USD"),
        ),
        (
            "dividend_row",
            Decimal("9.10") / Decimal("0.85600300"),
            "USD",
            "EUR",
            Decimal("0.85600300"),
            Decimal("9.10"),
            MoneyDto(amount=Decimal("0.0"), currency="USD"),
            MoneyDto(amount=Decimal("0.0"), currency="EUR"),
        ),
        (
            "currency_conversion_row",
            Decimal("4612.31"),
            "USD",
            "CZK",
            (Decimal("110165.25") / Decimal("4612.31")),
            Decimal("110000.0"),
            MoneyDto(amount=Decimal("0.0"), currency="USD"),
            MoneyDto(amount=Decimal("165.25"), currency="CZK"),
        ),
    ],
)
def test_parse_currency_conversion(
    request: pytest.FixtureRequest,
    report_parser: Trading212ReportParser,
    row_fixture: str,
    from_amount: Decimal,
    from_currency: str,
    to_currency: str,
    rate: Decimal,
    expected_to_amount: Decimal,
    expected_sell_fee: MoneyDto,
    expected_buy_fee: MoneyDto,
) -> None:
    row = request.getfixturevalue(row_fixture)

    currency_sell_details, currency_buy_details = (
        report_parser._parse_currency_conversion(
            row=row,
            from_amount=from_amount,
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            expected_to_amount=expected_to_amount,
        )
    )

    tolerance = Decimal("0.001")

    assert currency_sell_details.quantity == from_amount
    assert currency_sell_details.price == MoneyDto(amount=rate, currency=to_currency)
    assert currency_sell_details.fee == expected_sell_fee
    assert currency_sell_details.cash_impact == MoneyDto(
        amount=(from_amount * -1), currency=from_currency
    )

    assert abs(currency_buy_details.quantity - expected_to_amount) < tolerance
    assert currency_buy_details.price == MoneyDto(
        amount=(Decimal("1.0") / rate), currency=from_currency
    )
    assert currency_buy_details.fee == expected_buy_fee
    assert (
        abs(currency_buy_details.cash_impact.amount - expected_to_amount) < tolerance
    )
    assert currency_buy_details.cash_impact.currency == to_currency
