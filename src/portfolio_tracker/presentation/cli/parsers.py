import re
from datetime import date, datetime, time, timezone
from typing import Any, Callable, Literal, TypeVar, overload

import typer

TItem = TypeVar("TItem")


def validate_non_empty(value: str) -> str:
    value = value.strip()
    if not value:
        raise typer.BadParameter("Value is empty.")

    return value


def parse_date_parameter(value: str, formats: list[str] | None = None) -> date:
    if formats:
        for format_ in formats:
            try:
                return datetime.strptime(value, format_).date()
            except ValueError:
                continue

    return date.fromisoformat(value)


def parse_datetime_parameter(
    value: str, date_formats: list[str] | None = None
) -> datetime:
    parts = re.split(r"[T\s]+", value, maxsplit=1)
    date_value = parts[0]
    time_value = parts[1] if len(parts) > 1 else "00:00:00"

    date_ = parse_date_parameter(date_value, date_formats)
    time_ = time.fromisoformat(time_value)
    datetime_ = datetime.combine(date_, time_)

    return datetime_.astimezone(timezone.utc)


@overload
def parse_list_parameter(
    values: list[str] | None, converter: None = None
) -> list[str]: ...


@overload
def parse_list_parameter(
    values: list[str] | None, converter: Callable[[str], TItem]
) -> list[TItem]: ...


def parse_list_parameter(
    values: list[str] | None, converter: Callable[[str], TItem] | None = None
) -> list[TItem]:
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
