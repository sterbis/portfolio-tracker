import re
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Callable, Literal, TypeVar, overload

import typer
from filterutils import Filter, FilterTree

from portfolio_tracker.application.container import Container
from portfolio_tracker.application.views import MoneyView


TItem = TypeVar("TItem")


DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"]
MONEY_EXPRESSION_REGEX = re.compile(
    r"^\s*(?P<amount>\d+?)\s*(?P<currency>[a-zA-Z]{3})?\s*$"
)


def validate_non_empty(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Value is empty.")

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


def parse_datetime(
    value: str, *, date_formats: list[str] | None = None
) -> datetime:
    parts = re.split(r"[T\s]+", value, maxsplit=1)
    date_value = parts[0]
    time_value = parts[1] if len(parts) > 1 else "00:00:00"

    date_ = parse_date(date_value, formats=date_formats)
    time_ = time.fromisoformat(time_value)
    datetime_ = datetime.combine(date_, time_)

    return datetime_.astimezone(timezone.utc)


def parse_money(value: str, default_currency: str) -> MoneyView:
    match = MONEY_EXPRESSION_REGEX.match(value)
    if not match:
        raise ValueError(f"Invalid money expression: '{value}'")

    amount = match.group("amount")
    currency = match.group("currency") or default_currency
    return MoneyView(amount=Decimal(amount), currency=currency.upper())


def get_application_context(ctx: typer.Context) -> Container:
    context: Container = ctx.obj
    return context


def context_aware_date_parser(value: str, ctx: typer.Context) -> date:
    return parse_date(value, formats=get_application_context(ctx).DATE_FORMATS)


def context_aware_datetime_parser(value: str, ctx: typer.Context) -> datetime:
    return parse_datetime(value, date_formats=get_application_context(ctx).DATE_FORMATS)


def context_aware_money_parser(value: str, ctx: typer.Context) -> MoneyView:
    return parse_money(value, get_application_context(ctx).DEFAULT_REPORTING_CURRENCY)


@overload
def parse_list_parameter(
    values: list[str] | None, *, converter: None = None
) -> list[str]: ...


@overload
def parse_list_parameter(
    values: list[str] | None, *, converter: Callable[[str], TItem]
) -> list[TItem]: ...


def parse_list_parameter(
    values: list[str] | None, *, converter: Callable[[str], TItem] | None = None
) -> list[TItem] | list[str]:
    if not values:
        return []

    items: list[Any] = []
    for value in values:
        items.extend(
            converter(item.strip()) if converter else item.strip()
            for item in value.split(",")
            if item.strip()
        )

    return items


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


def build_filter(*parameters: Filter | None) -> FilterTree:
    filter_ = FilterTree()
    for parameter in parameters:
        if parameter:
            filter_.add_child(parameter)

    return filter_
