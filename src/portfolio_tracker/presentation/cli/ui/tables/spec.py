from dataclasses import dataclass, fields
from functools import cached_property
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Generic, Literal, Mapping, TypeVar

from rich.text import Text

from portfolio_tracker.presentation.cli.settings import CliDisplaySettings
from portfolio_tracker.presentation.cli.ui.fromatters import (
    format_bool,
    format_date,
    format_datetime,
    format_money,
    format_number,
    format_percent,
    format_profit_and_loss_money,
    format_profit_and_loss_percent,
)

TView = TypeVar("TView")
Justify = Literal["left", "center", "right"]


@dataclass(frozen=True, kw_only=True)
class ColumnSpec:
    field: str
    header: str | None = None
    style: str | None = None
    justify: Justify = "left"
    formatter: Callable[[Any, CliDisplaySettings], Text | str] | None = None
    formatter_handles_none: bool = False
    total_field: str | None = None

    def __post_init__(self) -> None:
        if self.formatter_handles_none and self.formatter is None:
            raise ValueError(
                "formatter_handles_none=True requires a formatter to be provided."
            )


def text_column(
    field: str,
    header: str | None = None,
    style: str | None = None,
    justify: Justify = "left",
) -> ColumnSpec:
    return ColumnSpec(
        field=field,
        header=header,
        style=style,
        justify=justify,
    )


def bool_column(
    field: str,
    header: str | None = None,
    style: str | None = None,
    justify: Justify = "center",
) -> ColumnSpec:
    return ColumnSpec(
        field=field,
        header=header,
        style=style,
        justify=justify,
        formatter=format_bool,
        formatter_handles_none=True,
    )


def date_column(
    field: str,
    header: str | None = None,
    style: str | None = None,
    justify: Justify = "left",
) -> ColumnSpec:
    return ColumnSpec(
        field=field,
        header=header,
        style=style,
        justify=justify,
        formatter=format_date,
    )


def datetime_column(
    field: str,
    header: str | None = None,
    style: str | None = None,
    justify: Justify = "left",
) -> ColumnSpec:
    return ColumnSpec(
        field=field,
        header=header,
        style=style,
        justify=justify,
        formatter=format_datetime,
    )


def number_column(
    field: str,
    header: str | None = None,
    style: str | None = None,
    justify: Justify = "right",
    decimal_places: int = 2,
    thousand_separator: bool = False,
    formatter: Callable[[Any, CliDisplaySettings], Text | str] | None = None,
) -> ColumnSpec:
    if formatter is None:

        def format_(value: Any, _: CliDisplaySettings) -> str:
            return format_number(value, decimal_places, thousand_separator)

        formatter = format_

    return ColumnSpec(
        field=field,
        header=header,
        style=style,
        justify=justify,
        formatter=formatter,
    )


def percent_column(
    field: str,
    header: str | None = None,
    style: str | None = None,
    justify: Justify = "right",
    profit_and_loss: bool = False,
    total_field: str | None = None,
) -> ColumnSpec:
    return ColumnSpec(
        field=field,
        header=header,
        style=style,
        justify=justify,
        formatter=format_profit_and_loss_percent if profit_and_loss else format_percent,
        total_field=total_field,
    )


def money_column(
    field: str,
    header: str | None = None,
    style: str | None = None,
    justify: Justify = "right",
    profit_and_loss: bool = False,
    total_field: str | None = None,
) -> ColumnSpec:
    return ColumnSpec(
        field=field,
        header=header,
        style=style,
        justify=justify,
        formatter=format_profit_and_loss_money if profit_and_loss else format_money,
        total_field=total_field,
    )


@dataclass(frozen=True, kw_only=True)
class TableSpec(Generic[TView]):
    name: ClassVar[str] = "undefined"
    title: ClassVar[str] = "undefined"

    @cached_property
    def columns(self) -> Mapping[str, ColumnSpec]:
        return MappingProxyType(
            {
                field.name: value
                for field in fields(self)
                if isinstance(value := getattr(self, field.name), ColumnSpec)
            }
        )

    def get_column_field(self, column_name: str) -> str:
        return self.columns[column_name].field
