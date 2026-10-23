from dataclasses import dataclass, fields
from decimal import Decimal
from enum import StrEnum
from functools import cached_property
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Generic, Mapping, TypeVar

from portfolio_tracker.settings import DisplaySettings
from portfolio_tracker.presentation.shared.fromatters import (
    format_bool,
    format_date,
    format_datetime,
    format_money,
    format_number,
    format_percent,
)
from portfolio_tracker.shared.dataclass_utils import resolve_field_value


TView = TypeVar("TView")
type ValueFormatter = Callable[[Any, DisplaySettings], str]


class Tone(StrEnum):
    DEFAULT = "default"
    PROFIT_OR_LOSS = "profit_or_loss"
    PROFIT = "profit"
    LOSS = "loss"


class HorizontalAlignment(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"


class ColumnKind(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    MONEY = "money"
    PERCENT = "percent"
    DATETIME = "datetime"


@dataclass(frozen=True, kw_only=True)
class ColumnSpec:
    title: str
    field: str
    total_field: str | None = None
    tone: Tone = Tone.DEFAULT
    kind: ColumnKind = ColumnKind.TEXT
    horizontal_alignment: HorizontalAlignment = HorizontalAlignment.LEFT
    formatter: ValueFormatter | None = None

    def get_value(self, obj: Any) -> Any:
        return resolve_field_value(obj, self.field)

    def get_total_value(self, obj: Any) -> Any | None:
        if self.total_field is None:
            return None

        return resolve_field_value(obj, self.total_field)

    def format_value(
        self,
        value: Any | None,
        settings: DisplaySettings,
        none_value: str | None = None,
    ) -> str:
        if value is None:
            return settings.none_value if none_value is None else none_value

        if self.formatter:
            return self.formatter(value, settings)

        return str(value)

    def get_tone(self, value: Any) -> Tone:
        if self.tone is not Tone.PROFIT_OR_LOSS:
            return self.tone

        amount = getattr(value, "amount", value)
        if isinstance(amount, (Decimal, int, float)):
            if amount > 0:
                return Tone.PROFIT
            if amount < 0:
                return Tone.LOSS

        return Tone.DEFAULT


def text_column(
    field: str,
    title: str,
    tone: Tone = Tone.DEFAULT,
    horizontal_alignment: HorizontalAlignment = HorizontalAlignment.LEFT,
) -> ColumnSpec:
    return ColumnSpec(
        field=field,
        title=title,
        tone=tone,
        horizontal_alignment=horizontal_alignment,
    )


def bool_column(
    field: str,
    title: str,
    tone: Tone = Tone.DEFAULT,
    horizontal_alignment: HorizontalAlignment = HorizontalAlignment.CENTER,
) -> ColumnSpec:
    return ColumnSpec(
        field=field,
        title=title,
        tone=tone,
        horizontal_alignment=horizontal_alignment,
        formatter=format_bool,
    )


def date_column(
    field: str,
    title: str,
    tone: Tone = Tone.DEFAULT,
    horizontal_alignment: HorizontalAlignment = HorizontalAlignment.LEFT,
) -> ColumnSpec:
    return ColumnSpec(
        field=field,
        title=title,
        tone=tone,
        horizontal_alignment=horizontal_alignment,
        formatter=format_date,
    )


def datetime_column(
    field: str,
    title: str,
    tone: Tone = Tone.DEFAULT,
    horizontal_alignment: HorizontalAlignment = HorizontalAlignment.LEFT,
) -> ColumnSpec:
    return ColumnSpec(
        field=field,
        title=title,
        tone=tone,
        horizontal_alignment=horizontal_alignment,
        formatter=format_datetime,
    )


def number_column(
    field: str,
    title: str,
    tone: Tone = Tone.DEFAULT,
    horizontal_alignment: HorizontalAlignment = HorizontalAlignment.RIGHT,
    decimal_places: int = 2,
    thousand_separator: bool = False,
    formatter: ValueFormatter | None = None
) -> ColumnSpec:
    if formatter is None:
        def format_(value: Any, _: DisplaySettings) -> str:
            return format_number(value, decimal_places, thousand_separator)

        formatter = format_

    return ColumnSpec(
        field=field,
        title=title,
        tone=tone,
        horizontal_alignment=horizontal_alignment,
        formatter=formatter,
    )


def percent_column(
    field: str,
    title: str,
    tone: Tone = Tone.DEFAULT,
    horizontal_alignment: HorizontalAlignment = HorizontalAlignment.RIGHT,
    total_field: str | None = None,
) -> ColumnSpec:
    return ColumnSpec(
        field=field,
        title=title,
        tone=tone,
        horizontal_alignment=horizontal_alignment,
        formatter=format_percent,
        total_field=total_field,
    )


def money_column(
    field: str,
    title: str,
    tone: Tone = Tone.DEFAULT,
    horizontal_alignment: HorizontalAlignment = HorizontalAlignment.RIGHT,
    total_field: str | None = None,
) -> ColumnSpec:
    return ColumnSpec(
        field=field,
        title=title,
        tone=tone,
        horizontal_alignment=horizontal_alignment,
        formatter=format_money,
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

    def __post_init__(self) -> None:
        titles = [column.title or column.field for column in self.columns.values()]
        if len(titles) != len(set(titles)):
            raise ValueError(f"Duplicate column titles in table spec '{self.name}'.")

    def get_column_field(self, column_name: str) -> str:
        return self.columns[column_name].field
