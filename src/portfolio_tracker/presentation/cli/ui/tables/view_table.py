import functools
from dataclasses import dataclass
from typing import Any, Callable, Generic, Literal, TypeVar

from rich.table import Table
from rich.text import Text

from portfolio_tracker.presentation.cli.settings import CliDisplaySettings
from portfolio_tracker.shared.dataclass_utils import resolve_field_value

from ..fromatters import (
    format_datetime,
    format_money,
    format_profit_and_loss_money,
    format_quantity,
    format_percent,
    format_profit_and_loss_percent,
)

TView = TypeVar("TView")
Justify = Literal["left", "center", "right"]


@dataclass(frozen=True, kw_only=True)
class Column:
    field: str
    header: str | None = None
    style: str | None = None
    justify: Justify = "left"
    formatter: Callable[[Any, CliDisplaySettings], Text | str] | None = None
    total_field: str | None = None

    def extract(self, view: Any) -> Any:
        return resolve_field_value(view, self.field)

    def render_header(self, _: CliDisplaySettings) -> Text | str:
        if self.header is None:
            return ""

        return Text(
            text=self.header,
            style="",
            justify="center",
            overflow="fold",
            no_wrap=False,
        )

    def render_cell(self, view: Any, settings: CliDisplaySettings) -> Text | str:
        value = resolve_field_value(view, self.field)
        return self._format_value(value, settings, none_string=settings.none_string)

    def render_footer(
        self, total_view: Any, settings: CliDisplaySettings
    ) -> Text | str:
        if self.total_field is None:
            return ""

        value = resolve_field_value(total_view, self.total_field)
        return self._format_value(value, settings)

    def _format_value(
        self, value: Any | None, settings: CliDisplaySettings, none_string: str = ""
    ) -> Text | str:
        if value is None:
            return none_string

        if self.formatter:
            return self.formatter(value, settings)

        return str(value)


def text_column(
    field: str,
    header: str | None = None,
    style: str | None = None,
    justify: Justify = "left",
) -> Column:
    return Column(
        field=field,
        header=header,
        style=style,
        justify=justify,
    )


def datetime_column(
    field: str,
    header: str | None = None,
    style: str | None = None,
    justify: Justify = "left",
) -> Column:
    return Column(
        field=field,
        header=header,
        style=style,
        justify=justify,
        formatter=format_datetime,
    )


def quantity_column(
    field: str,
    header: str | None = None,
    style: str | None = None,
    justify: Justify = "right",
) -> Column:
    return Column(
        field=field,
        header=header,
        style=style,
        justify=justify,
        formatter=format_quantity,
    )


def percent_column(
    field: str,
    header: str | None = None,
    style: str | None = None,
    justify: Justify = "right",
    profit_and_loss: bool = False,
) -> Column:
    return Column(
        field=field,
        header=header,
        style=style,
        justify=justify,
        formatter=format_profit_and_loss_percent if profit_and_loss else format_percent,
    )


def money_column(
    field: str,
    header: str | None = None,
    style: str | None = None,
    justify: Justify = "right",
    profit_and_loss: bool = False,
    total_field: str | None = None,
) -> Column:
    return Column(
        field=field,
        header=header,
        style=style,
        justify=justify,
        formatter=format_profit_and_loss_money if profit_and_loss else format_money,
        total_field=total_field,
    )


class ViewTable(Generic[TView]):
    _columns: dict[str, Column] = {}
    name = "undefined"
    title = "undefined"

    def __init_subclass__(cls) -> None:
        cls._columns = cls._columns.copy()
        for name, value in cls.__dict__.items():
            if isinstance(value, Column):
                cls._columns[name] = value

    def _sort_key(self, view: TView, column_name: str, reverse: bool) -> tuple[bool, Any]:
        value = resolve_field_value(view, self._columns[column_name].field)
        return value is not None if reverse else value is None, value

    def sort(self, views: list[TView], sort_columns: list[str]) -> list[TView]:
        sorted_views = list(views)
        for sort_column in reversed(sort_columns):
            column_name = sort_column.lstrip("-")
            reverse = sort_column.startswith("-")
            sorted_views.sort(
                key=functools.partial(
                    self._sort_key, column_name=column_name, reverse=reverse
                ),
                reverse=reverse,
            )

        return sorted_views

    def render(
        self,
        views: list[TView],
        settings: CliDisplaySettings,
        *,
        title: str | None = None,
        active_columns: list[str] | None = None,
        sort_columns: list[str] | None = None,
        total_view: Any | None = None
    ) -> Table:
        title = title or self.title
        active_columns = active_columns or list(self._columns)
        if sort_columns:
            views = self.sort(views, sort_columns)

        table = Table(title=title, show_footer=total_view is not None)

        columns = [self._columns[column_name] for column_name in active_columns]
        for column in columns:
            footer = column.render_footer(total_view, settings) if total_view else ""
            table.add_column(
                header=column.render_header(settings),
                header_style="bold",
                footer=footer,
                footer_style="bold",
                style=column.style,
                justify=column.justify,
                no_wrap=True,
            )

        for view in views:
            table.add_row(
                *[column.render_cell(view, settings) for column in columns]
            )

        return table

    @classmethod
    def render_configuration(
        cls,
        *,
        active_columns: list[str] | None = None,
        default_active_columns: list[str] | None = None,
        sort_columns: list[str] | None = None,
        default_sort_columns: list[str] | None = None,
    ) -> Table:
        active_columns = active_columns or list(cls._columns)
        default_active_columns = default_active_columns or []
        sort_columns = sort_columns or []
        default_sort_columns = default_sort_columns or []

        table = Table(title=f"{cls.title} Table Configuration")
        table.add_column("Name")
        table.add_column("Active", justify="center")
        table.add_column("Default Active", justify="center")
        table.add_column("Sort", justify="center")
        table.add_column("Default Sort", justify="center")

        for column in sorted(cls._columns):
            values: list[str] = []
            for columns in (
                active_columns,
                default_active_columns,
                sort_columns,
                default_sort_columns,
            ):
                if column in columns:
                    order = columns.index(column) + 1
                    value = f":white_check_mark: [dim]({order})[/]"
                else:
                    value = "[dim]--[/]"

                values.append(value)

            table.add_row(column, *values)

        return table

    @classmethod
    def get_column_field(cls, column_name: str) -> str:
        return cls._columns[column_name].field
