import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from portfolio_tracker.domain.shared import Currency, Money


@pytest.mark.parametrize(
    "value, column_type, expected_raw_data_type, expected_raw_value",
    [
        (date(2026, 7, 4), "DATE", "text", "2026-07-04"),
        (
            datetime(2026, 7, 4, 12, 0, 0, tzinfo=timezone.utc),
            "DATETIME",
            "text",
            "2026-07-04T12:00:00+00:00",
        ),
        (
            Decimal("0.0001234567890123456789"),
            "DECIMAL_AS_TEXT",
            "text",
            "0.0001234567890123456789",
        ),
        (
            Decimal("0.0001234567890123456789"),
            "DECIMAL",
            "real",
            0.00012345678901234567,
        ),
        (
            Money(amount=Decimal("12.34"), currency=Currency.USD),
            "MONEY",
            "text",
            "12.34;USD",
        ),
    ],
)
def test_adapters(
    value: Any,
    column_type: str,
    expected_raw_data_type: str,
    expected_raw_value: str,
) -> None:
    connection = sqlite3.connect(":memory:", detect_types=0)
    cursor = connection.cursor()

    try:
        cursor.execute(f"CREATE TABLE test_table (value {column_type});")
        cursor.execute("INSERT INTO test_table VALUES (?);", (value,))
        cursor.execute("SELECT typeof(value), value FROM test_table;")

        raw_data_type, raw_value = cursor.fetchone()
        assert raw_data_type == expected_raw_data_type
        assert raw_value == expected_raw_value

    finally:
        connection.close()


@pytest.mark.parametrize(
    "raw_value, column_type, expected_value",
    [
        ("2026-07-04", "DATE", date(2026, 7, 4)),
        (
            "2026-07-04T12:00:00+00:00",
            "DATETIME",
            datetime(2026, 7, 4, 12, 0, 0, tzinfo=timezone.utc),
        ),
        (
            "0.0001234567890123456789",
            "DECIMAL_AS_TEXT",
            Decimal("0.0001234567890123456789"),
        ),
        ("12.34;USD", "MONEY", Money(amount=Decimal("12.34"), currency=Currency.USD)),
    ],
)
def test_converters(
    raw_value: str,
    column_type: str,
    expected_value: Any,
) -> None:
    connection = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()

    try:
        cursor.execute(f"CREATE TABLE test_table (value {column_type});")
        cursor.execute(f"INSERT INTO test_table VALUES ('{raw_value}');")
        cursor.execute("SELECT value FROM test_table;")

        value = cursor.fetchone()[0]
        assert value == expected_value

    finally:
        connection.close()
