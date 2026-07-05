import sqlite3
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from portfolio_tracker.domain.shared import Money


def adapt_date(value: date) -> str:
    return value.isoformat()


def adapt_datetime(value: datetime) -> str:
    return value.isoformat()


def adapt_decimal(value: Decimal) -> str:
    return str(value.normalize())


def adapt_enum(value: StrEnum) -> str:
    return value.value


def adapt_money(value: Money) -> str:
    return f"{adapt_decimal(value.amount)};{value.currency}"


def convert_date(value: bytes) -> date:
    return date.fromisoformat(value.decode())


def convert_datetime(value: bytes) -> datetime:
    return datetime.fromisoformat(value.decode())


def convert_decimal(value: bytes | str) -> Decimal:
    if isinstance(value, bytes):
        value = value.decode()
    return Decimal(str(value))


def convert_money(value: bytes) -> Money:
    amount, currency = value.split(b";")
    return Money(amount=convert_decimal(amount), currency=currency.decode())


_MAPPERS_REGISTERED = False


def register_mappers() -> None:
    global _MAPPERS_REGISTERED  # pylint: disable=global-statement

    if not _MAPPERS_REGISTERED:
        sqlite3.register_adapter(date, adapt_date)
        sqlite3.register_adapter(datetime, adapt_datetime)
        sqlite3.register_adapter(Decimal, adapt_decimal)
        sqlite3.register_adapter(Money, adapt_money)

        sqlite3.register_converter("date", convert_date)
        sqlite3.register_converter("datetime", convert_datetime)
        sqlite3.register_converter("decimal_as_text", convert_decimal)
        sqlite3.register_converter("money", convert_money)

        _MAPPERS_REGISTERED = True
