from dataclasses import is_dataclass
from typing import Annotated, Any

import typer

from portfolio_tracker.presentation.cli.console import console
from portfolio_tracker.presentation.cli.context import (
    get_environment,
    get_logged_in_user_id,
    get_settings,
    get_settings_cache,
)
from portfolio_tracker.presentation.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.cli.parsers import parse_settings_value
from portfolio_tracker.presentation.cli.settings import TableDisplaySettings
from portfolio_tracker.presentation.cli.ui.fromatters import format_settings_values
from portfolio_tracker.presentation.cli.ui.tables import get_view_table_by_name
from portfolio_tracker.shared.dataclass_utils import (
    resolve_field_value,
    unstructure,
)
from portfolio_tracker.shared.settings_utils import merge_dicts
from portfolio_tracker.settings import Settings


settings_app = GuardedTyper()


@settings_app.command(name="list")
def list_settings(
    ctx: typer.Context,
    key: Annotated[str | None, typer.Argument()] = None,
    as_json: Annotated[bool, typer.Option("--json/--no-json")] = False,
) -> None:
    user_id = get_logged_in_user_id(ctx)
    cache = get_settings_cache(ctx)

    overrides = cache.get_overrides(user_id)
    if key:
        settings = _resolve_settings_section(cache.default_settings, key)
        for section_key in key.split("."):
            overrides = overrides.get(section_key, {})

    else:
        settings = cache.default_settings

    if as_json:
        default_values = unstructure(settings)
        values = merge_dicts(default_values, overrides)
        console.print_json(data=values)
        return

    if isinstance(settings, TableDisplaySettings):
        assert key is not None
        table_name = key.split(".")[-1]
        view_table = get_view_table_by_name(table_name)

        configuration = view_table.render_configuration(
            active_columns=overrides.get("active_columns", settings.active_columns),
            default_active_columns=settings.active_columns,
            sort_columns=overrides.get("sort_columns", settings.sort_columns),
            default_sort_columns=settings.sort_columns,
        )

        console.print(configuration)
        console.print(
            "\n"
            f"To change displayed columns run: portfolio settings set display.cli.tables.{table_name}.active_columns name1,name2...\n"
            f"To change sort order run: portfolio settings set display.cli.tables.{table_name}.sort_columns name1,name2...\n"
            f"To reset table configuration run: portfolio settings reset display.cli.tables.{table_name}\n"
        )

    else:
        default_values = unstructure(settings)
        lines = format_settings_values(default_values, overrides, key)
        console.print("\n".join(lines))


@settings_app.command(name="get")
def get_settings_value(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument()],
) -> None:
    user_id = get_logged_in_user_id(ctx)
    settings = get_settings(ctx, user_id)
    value = _resolve_settings_value(settings, key)
    console.print(unstructure(value))


@settings_app.command(name="set")
def set_settings_value(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument()],
    value: Annotated[str, typer.Argument()],
) -> None:
    user_id = get_logged_in_user_id(ctx)
    cache = get_settings_cache(ctx)

    try:
        override_value = parse_settings_value(Settings, key, value)

    except (KeyError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error

    cache.set_value(user_id, key, override_value)
    console.print(f"Settings '{key}' value sucessfully updated.")


@settings_app.command(name="reset")
def reset_settings(
    ctx: typer.Context,
    key: Annotated[str | None, typer.Argument()] = None,
    all_: Annotated[bool, typer.Option()] = False,
) -> None:
    if not key and not all_ or key and all_:
        raise typer.BadParameter(
            "Specify a key to reset, or use '--all' to reset all settings."
        )

    environment = get_environment(ctx)
    cache = get_settings_cache(ctx)
    user_id = get_logged_in_user_id(ctx)

    if all_:
        if environment.is_interactive:
            reset_all = typer.confirm(
                "Are you sure you want to reset all settings to defaults?",
                default=False,
            )
            if not reset_all:
                console.print("Operation cancelled.")
                return
                
        cache.reset_all(user_id)
        console.print("All settings sucessfully reset to defaults.")
        return

    assert key is not None
    _resolve_settings_section(cache.default_settings, key)
    _, was_reset = cache.reset_value(user_id, key)
    if was_reset:
        console.print(f"Settings '{key}' value sucessfully reset to default.")

    else:
        console.print(f"Settings '{key}' already has default value.")


def _resolve_settings_section(settings: Settings, key: str) -> Any:
    try:
        return resolve_field_value(settings, key)
    except (AttributeError, KeyError) as error:
        raise typer.BadParameter(f"Invalid settings key: '{key}'.") from error


def _resolve_settings_value(settings: Settings, key: str) -> Any:
    value = _resolve_settings_section(settings, key)

    if is_dataclass(value) or isinstance(value, dict):
        raise KeyError(f"Invalid settings key: '{key}'. Key points to a section.")

    return value
