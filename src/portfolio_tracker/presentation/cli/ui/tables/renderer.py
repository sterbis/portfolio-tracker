from typing import Any, Iterable, TypeVar

from rich.table import Table
from rich.text import Text

from portfolio_tracker.presentation.cli.console import console
from portfolio_tracker.presentation.cli.settings import (
    CliDisplaySettings,
    TableDisplaySettings,
)
from portfolio_tracker.shared.dataclass_utils import resolve_field_value

from .registry import get_table_spec
from .spec import ColumnSpec, TableSpec

TView = TypeVar("TView")


class TableRenderer:
    def render(
        self,
        spec: TableSpec[TView],
        views: Iterable[TView],
        settings: CliDisplaySettings,
        *,
        title: str | None = None,
        columns: list[str] | None = None,
        total_view: Any | None = None,
    ) -> Table:
        title = title or spec.title
        columns = columns or list(spec.columns)

        table = Table(title=title, show_footer=total_view is not None)

        column_specs = [spec.columns[column] for column in columns]
        for column_spec in column_specs:
            footer = (
                self._render_footer(column_spec, total_view, settings)
                if total_view
                else ""
            )
            table.add_column(
                header=self._render_header(column_spec),
                header_style="bold",
                footer=footer,
                footer_style="bold",
                style=column_spec.style,
                justify=column_spec.justify,
                no_wrap=True,
            )

        for view in views:
            table.add_row(
                *[
                    self._render_cell(column_spec, view, settings)
                    for column_spec in column_specs
                ]
            )

        return table

    def render_settings(
        self,
        spec: TableSpec[TView],
        settings: TableDisplaySettings,
        *,
        active_columns: list[str] | None = None,
        sort_columns: list[str] | None = None,
    ) -> Table:
        default_active_columns = settings.active_columns
        active_columns = active_columns or default_active_columns
        default_sort_columns = settings.sort_columns
        sort_columns = sort_columns or default_sort_columns

        table = Table(title=f"{spec.title} Table Settings")
        table.add_column("Name")
        table.add_column("Active", justify="center")
        table.add_column("Default Active", justify="center")
        table.add_column("Sort", justify="center")
        table.add_column("Default Sort", justify="center")

        for column in sorted(spec.columns):
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

    def _render_header(self, spec: ColumnSpec) -> Text | str:
        if spec.header is None:
            return ""

        return Text(
            text=spec.header,
            style="",
            justify="center",
            overflow="fold",
            no_wrap=False,
        )

    def _render_cell(
        self, spec: ColumnSpec, view: Any, settings: CliDisplaySettings
    ) -> Text | str:
        value = resolve_field_value(view, spec.field)
        return self._format_value(spec, value, settings, none_value=settings.none_value)

    def _render_footer(
        self, spec: ColumnSpec, total_view: Any, settings: CliDisplaySettings
    ) -> Text | str:
        if spec.total_field is None:
            return ""

        value = resolve_field_value(total_view, spec.total_field)
        return self._format_value(spec, value, settings)

    def _format_value(
        self,
        spec: ColumnSpec,
        value: Any | None,
        settings: CliDisplaySettings,
        none_value: str = "",
    ) -> Text | str:
        if value is None and not spec.formatter_handles_none:
            return none_value

        if spec.formatter:
            return spec.formatter(value, settings)

        return str(value)


def display_table(
    view_cls: type[TView],
    views: Iterable[TView],
    settings: CliDisplaySettings,
    *,
    title: str | None = None,
    columns: list[str] | None = None,
    total_view: Any | None = None,
) -> None:
    spec = get_table_spec(view_cls)
    columns = columns or settings.tables[spec.name].active_columns
    renderer = TableRenderer()
    table = renderer.render(
        spec,
        views,
        settings,
        title=title,
        columns=columns,
        total_view=total_view,
    )
    console.print(table)
