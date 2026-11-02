from dataclasses import is_dataclass
from typing import Annotated, Any

import click
import typer

from portfolio_tracker.presentation.desktop.cli.console import console
from portfolio_tracker.presentation.desktop.cli.context import CliContext
from portfolio_tracker.presentation.desktop.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.desktop.cli.parsers import parse_settings_value
from portfolio_tracker.presentation.shared.settings import TableDisplaySettings
from portfolio_tracker.presentation.shared.fromatters import format_settings_values
from portfolio_tracker.presentation.shared.tables import get_table_spec_by_name
from portfolio_tracker.presentation.desktop.cli.table import TableRenderer
from portfolio_tracker.settings import Settings
from portfolio_tracker.shared.dataclass_utils import (
    replace_dict_values,
    resolve_field_value,
    unstructure,
)
from portfolio_tracker.shared.settings_utils import SettingsValidationError

settings_app = GuardedTyper()


@settings_app.command(name="list", allow_default_settings=True)
def list_settings(
    ctx: typer.Context,
    key: Annotated[str | None, typer.Argument()] = None,
    as_json: Annotated[bool, typer.Option("--json/--no-json")] = False,
) -> None:
    context: CliContext = ctx.obj

    default_settings = context.settings_cache.default_settings
    overrides = context.settings_cache.get_overrides(context.user_id)
    if key:
        default_settings = _resolve_settings_value(default_settings, key)
        for section_key in key.split("."):
            overrides = overrides.get(section_key, {})

    if as_json:
        console.print_json(
            data=replace_dict_values(
                unstructure(default_settings), unstructure(overrides)
            )
        )
        return

    if isinstance(default_settings, TableDisplaySettings):
        assert key is not None
        table_name = key.split(".")[-1]
        table_spec = get_table_spec_by_name(table_name)
        settings_table = TableRenderer().render_settings(
            table_spec,
            default_settings,
            active_columns=overrides.get("active_columns"),
            sort_columns=overrides.get("sort_columns"),
        )

        console.print(settings_table)
        console.print(
            "\n"
            f"To change displayed columns run: portfolio settings set display.cli.tables.{table_name}.active_columns name1,name2...\n"
            f"To change sort order run: portfolio settings set display.cli.tables.{table_name}.sort_columns name1,name2...\n"
            f"To reset table configuration run: portfolio settings reset display.cli.tables.{table_name}\n"
        )

    else:
        lines = format_settings_values(
            unstructure(default_settings), unstructure(overrides), key
        )
        console.print("\n".join(lines))


@settings_app.command(name="get")
def get_settings_value(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument()],
) -> None:
    context: CliContext = ctx.obj
    value = _resolve_settings_value(context.settings, key)
    if is_dataclass(value) or isinstance(value, dict):
        raise typer.BadParameter(
            f"Invalid settings key: '{key}'. Key points to a section."
        )

    console.print(unstructure(value))


@settings_app.command(name="set", allow_invalid_settings=True)
def set_settings_value(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument()],
    value: Annotated[str, typer.Argument()],
) -> None:
    context: CliContext = ctx.obj

    try:
        resolved_value = parse_settings_value(Settings, key, value)
    except (KeyError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error

    try:
        context.settings_cache.set_value(context.user_id, key, resolved_value)
    except SettingsValidationError as error:
        raise typer.BadParameter(f"Invalid '{key}' settings value: {error}.") from error

    console.print(f"Settings '{key}' value sucessfully updated.")


@settings_app.command(name="reset", allow_invalid_settings=True)
def reset_settings(
    ctx: typer.Context,
    key: Annotated[str | None, typer.Argument()] = None,
    all_: Annotated[bool, typer.Option()] = False,
) -> None:
    if not key and not all_ or key and all_:
        raise click.UsageError(
            "Specify a key to reset or use '--all' to reset all settings."
        )

    context: CliContext = ctx.obj
    user_id = context.user_id
    settings_cache = context.settings_cache

    if all_:
        if context.environment.is_interactive:
            reset_all = typer.confirm(
                "Are you sure you want to reset all settings to defaults?",
                default=False,
            )
            if not reset_all:
                return

        settings_cache.reset_all(user_id)
        console.print("All settings sucessfully reset to defaults.")
        return

    assert key is not None
    _resolve_settings_value(settings_cache.default_settings, key)
    was_reset = settings_cache.reset_value(user_id, key)
    if was_reset:
        console.print(f"Settings '{key}' value sucessfully reset to default.")

    else:
        console.print(f"Settings '{key}' already has default value.")


def _resolve_settings_value(settings: Settings, key: str) -> Any:
    try:
        return resolve_field_value(settings, key)
    except (AttributeError, KeyError) as error:
        raise typer.BadParameter(f"Invalid settings key: '{key}'.") from error
