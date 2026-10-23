from typing import Any, Iterable, TypeVar

from rich.table import Table
from rich.text import Text

from portfolio_tracker.presentation.desktop.cli.console import console
from portfolio_tracker.settings import (
    DisplaySettings,
    TableDisplaySettings,
)
from portfolio_tracker.presentation.shared.tables import get_table_spec, ColumnSpec, TableSpec, Tone

TView = TypeVar("TView")


STYLES = {
    Tone.PROFIT: "profit",
    Tone.LOSS: "loss",
    Tone.DEFAULT: "",
}


class TableRenderer:
    def render(
        self,
        spec: TableSpec[TView],
        views: Iterable[TView],
        settings: DisplaySettings,
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
                style=column_spec.tone,
                justify=column_spec.horizontal_alignment.value,
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
        if spec.title is None:
            return ""

        return Text(
            text=spec.title,
            style="",
            justify="center",
            overflow="fold",
            no_wrap=False,
        )

    def _render_cell(
        self, spec: ColumnSpec, view: Any, settings: DisplaySettings
    ) -> Text | str:
        value = spec.get_value(view)
        formatted_value = spec.format_value(value, settings)
        return self._style_value(value, formatted_value, spec)

    def _render_footer(
        self, spec: ColumnSpec, total_view: Any, settings: DisplaySettings
    ) -> Text | str:
        value = spec.get_total_value(total_view)
        formatted_value = spec.format_value(value, settings, none_value="")
        return self._style_value(value, formatted_value, spec)

    def _style_value(
        self, value: Any | None, formatted_value: str, spec: ColumnSpec
    ) -> Text:
        tone = spec.get_tone(value)
        return Text(formatted_value, STYLES.get(tone, ""))


def display_table(
    view_cls: type[TView],
    views: Iterable[TView],
    settings: DisplaySettings,
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
