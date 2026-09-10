import re
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Callable, Literal, TypeVar

import typer

from portfolio_tracker.application.views import MoneyView
from portfolio_tracker.domain.shared import Currency

TParsedValue = TypeVar("TParsedValue")
TEnum = TypeVar("TEnum", bound=StrEnum)


DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"]
MONEY_EXPRESSION_REGEX = re.compile(
    r"^\s*(?P<amount>\d+?)\s*(?P<currency>[a-zA-Z]{3})?\s*$"
)


def validate_non_empty(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Value is empty.")

    return value


def allow_empty(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None

    return value


def parse_multi_value(value: str, *, separator: str = ",") -> list[str]:
    return [item.strip() for item in value.split(separator) if item.strip()]


def parse_key_value_pairs(value: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    seen_keys: set[str] = set()

    for item in value:
        key, separator, val = item.partition("=")
        if not separator:
            raise ValueError(f"Expected KEY=VALUE, got '{item}'.")

        key = key.strip().lower()
        if key in seen_keys:
            raise ValueError(f"Duplicate key '{key}'.")

        seen_keys.add(key)
        values[key] = val.strip()

    return values


def parse_date(value: str, *, formats: list[str] | None = None) -> date:
    if formats:
        for format_ in formats:
            try:
                return datetime.strptime(value, format_).date()
            except ValueError:
                continue

    return date.fromisoformat(value)


def date_parser(value: str) -> date:
    return parse_date(value, formats=DATE_FORMATS)


def parse_datetime(value: str, *, date_formats: list[str] | None = None) -> datetime:
    parts = re.split(r"[T\s]+", value, maxsplit=1)
    date_value = parts[0]
    time_value = parts[1] if len(parts) > 1 else "00:00:00"

    date_ = parse_date(date_value, formats=date_formats)
    time_ = time.fromisoformat(time_value)
    datetime_ = datetime.combine(date_, time_)

    return datetime_.astimezone(timezone.utc)


def datetime_parser(value: str) -> datetime:
    return parse_datetime(value, date_formats=DATE_FORMATS)


def parse_enum(value: str, enum_cls: type[TEnum]) -> TEnum:
    return enum_cls(value.upper())


def enum_parser(enum_cls: type[TEnum]) -> Callable[[str], TEnum]:
    def parser(value: str) -> TEnum:
        return parse_enum(value, enum_cls)

    return parser


def parse_money(value: str, *, default_currency: Currency | None = None) -> MoneyView:
    match = MONEY_EXPRESSION_REGEX.match(value)
    if not match:
        raise ValueError(f"Invalid money expression: '{value}'")

    amount = match.group("amount")
    if currency_code := match.group("currency"):
        currency = parse_enum(currency_code, Currency)

    elif default_currency:
        currency = default_currency

    else:
        raise ValueError(f"Missing currency in money expression: '{value}'")

    return MoneyView(amount=Decimal(amount), currency=currency)


def money_parser(default_currency: Currency) -> Callable[[str], MoneyView]:
    def parser(value: str) -> MoneyView:
        return parse_money(value, default_currency=default_currency)

    return parser


def parse_sort_parameter(value: str) -> tuple[str, Literal["ASC", "DESC"]]:
    parts = value.split(":", 1)
    column = parts[0].strip()

    if not column:
        raise typer.BadParameter("Sort column name cannot be empty.")

    if len(parts) == 1:
        return (column, "ASC")

    direction = parts[1].strip().upper()
    if direction not in ("ASC", "DESC"):
        raise typer.BadParameter(
            f"Invalid sort direction '{parts[1]}' for column '{column}'. Use 'asc' or 'desc'."
        )

    return (column, direction)  # type: ignore[return-value]


def parse_input_value(
    parameter: str,
    value: str,
    value_parser: Callable[[str], TParsedValue],
) -> TParsedValue:
    try:
        return value_parser(value)

    except ValueError as error:
        raise typer.BadParameter(f"Parameter: {parameter}. Reason: {error}") from error
