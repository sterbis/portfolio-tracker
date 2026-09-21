import re
import types
import typing
from dataclasses import is_dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import StrEnum
from types import NoneType
from typing import Any, Callable, TypeVar

from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.application.views import MoneyView
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.presentation.cli.ui.tables import get_view_table
from portfolio_tracker.shared.dataclass_utils import (
    register_converter,
    resolve_field_type,
    structure,
)

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


def parse_none(value: str) -> None:
    if value.strip().lower() in ("none", "null"):
        return None

    raise ValueError(f"Unexpected None value: '{value}'.")


def parse_bool(value: str) -> bool:
    normalized_value = value.strip().lower()
    if normalized_value in ("true", "1", "yes", "on"):
        return True

    if normalized_value in ("false", "0", "no", "off"):
        return False

    raise ValueError(f"Unexpected boolean value: '{value}'.")


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


def parse_sort_column(value: str, view_cls: type) -> Sort:
    if value.lower().endswith((":asc", "=asc", ":desc", "=desc")):
        column_name = value.split(":", 1)[0].split("=", 1)[0]
        reverse = value.lower().endswith("desc")

    elif value.startswith("-"):
        column_name = value[1:]
        reverse = True

    else:
        column_name = value
        reverse = False

    view_table = get_view_table(view_cls)
    field = view_table.get_column_field(column_name)

    return Sort(field=field, item_type=view_cls, reverse=reverse)


def sort_column_parser(view_cls: type) -> Callable[[str], Sort]:
    def parser(value: str) -> Sort:
        return parse_sort_column(value, view_cls)

    return parser


register_converter(NoneType, parse_none)
register_converter(bool, parse_bool)
register_converter(date, date_parser)
register_converter(datetime, datetime_parser)


def parse_settings_value(settings_cls: type, key: str, value: str) -> Any:
    try:
        field_type = resolve_field_type(settings_cls, key)
    except ValueError as error:
        raise KeyError(f"Invalid settings key: '{key}'.") from error

    if is_dataclass(field_type):
        raise KeyError(f"Invalid settings key: '{key}'. Key points to a section.")

    if origin_type := typing.get_origin(field_type):
        if origin_type is list and len(typing.get_args(field_type)) == 1:
            item_type = typing.get_args(field_type)[0]
            try:
                return [
                    structure(item, item_type)
                    for item in value.split(",")
                    if item.strip()
                ]
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid '{key}' settings value: '{value}'."
                ) from error

        if origin_type in (typing.Union, types.UnionType):
            for field_type in typing.get_args(field_type):
                try:
                    return structure(value, field_type)
                except TypeError, ValueError:
                    pass

            raise ValueError(f"Invalid '{key}' settings value: '{value}'.")

        raise KeyError(f"Invalid settings key: '{key}'.")

    try:
        return structure(value, field_type)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid '{key}' settings value: '{value}'.") from error
