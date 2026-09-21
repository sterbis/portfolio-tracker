from datetime import date, datetime
from decimal import Decimal
from functools import wraps
from typing import Any, Callable

from portfolio_tracker.application.views import MoneyView
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.presentation.cli.settings import CliDisplaySettings

Number = int | float | Decimal

CURRENCY_SYMBOLS = {
    Currency.USD: "$",
    Currency.EUR: "€",
}

CURRENCY_ABBREVIATIONS = {
    Currency.CZK: "Kč",
}

CHECK_ICON = "[green]\N{HEAVY CHECK MARK}[/green]"
CROSS_ICON = "[red]\N{HEAVY BALLOT X}[/red]"


class _UndefinedType:
    pass


_UNDEFINED = _UndefinedType()


def format_profit_and_loss[TValue: (Number, MoneyView)](
    func: Callable[[TValue, CliDisplaySettings], str],
) -> Callable[[TValue, CliDisplaySettings], str]:
    @wraps(func)
    def formatter(value: TValue, settings: CliDisplaySettings) -> str:
        amount = value.amount if isinstance(value, MoneyView) else value
        formatted_value = func(value, settings)

        if amount > 0:
            return f"[green]{formatted_value}[/]"

        if amount < 0:
            return f"[red]{formatted_value}[/]"

        return formatted_value

    return formatter


def format_bool(value: bool, _: CliDisplaySettings) -> str:
    return CHECK_ICON if value else CROSS_ICON


def format_date(value: date, settings: CliDisplaySettings) -> str:
    return value.strftime(settings.date_format)


def format_datetime(value: datetime, settings: CliDisplaySettings) -> str:
    formatted_value = value.astimezone().strftime(
        f"{settings.date_format} {settings.time_format}"
    )
    if settings.time_format.endswith("%f"):
        return formatted_value[:-3]

    return formatted_value


def format_number(
    value: Number, decimal_places: int, thousand_separator: bool = False
) -> str:
    separator = "," if thousand_separator else ""
    return f"{value:{separator}.{decimal_places}f}"


def format_quantity(value: Decimal, settings: CliDisplaySettings) -> str:
    return format_number(
        value, settings.quantity_decimal_places, thousand_separator=False
    )


def format_percent(value: Number, settings: CliDisplaySettings) -> str:
    return f"{format_number(value, settings.percent_decimal_places, thousand_separator=True)} %"


@format_profit_and_loss
def format_profit_and_loss_percent(value: Number, settings: CliDisplaySettings) -> str:
    return format_percent(value, settings)


def format_money(value: MoneyView, settings: CliDisplaySettings) -> str:
    formatted_amount = format_number(
        value.amount, settings.money_decimal_places, thousand_separator=True
    )
    if currency_symbol := CURRENCY_SYMBOLS.get(value.currency):
        return f"{currency_symbol}{formatted_amount}"

    if currency_abbreviation := CURRENCY_ABBREVIATIONS.get(value.currency):
        return f"{formatted_amount} {currency_abbreviation}"

    return f"{formatted_amount} {value.currency.value}"


@format_profit_and_loss
def format_profit_and_loss_money(value: MoneyView, settings: CliDisplaySettings) -> str:
    return format_money(value, settings)


def format_settings_values(
    default_values: dict[str, Any],
    overrides: dict[str, Any] | _UndefinedType = _UNDEFINED,
    section: str | None = None,
) -> list[str]:
    lines: list[str] = []
    overrides = {} if isinstance(overrides, _UndefinedType) else overrides

    for section_key, default_value in default_values.items():
        key = f"{section}.{section_key}" if section else section_key
        override_value = overrides.get(section_key, _UNDEFINED)

        if isinstance(default_value, dict):
            if not isinstance(override_value, (dict, _UndefinedType)):
                raise ValueError(
                    f"Invalid '{key}' settings override value: '{override_value}'."
                )

            lines.extend(format_settings_values(default_value, override_value, key))

        else:
            formatted_value = format_settings_value(default_value, override_value)
            lines.append(f"{key}={formatted_value}")

    return lines


def format_settings_value(value: Any, override_value: Any = _UNDEFINED) -> str:
    if isinstance(value, list):
        formatted_value = ", ".join(str(item) for item in value)

    else:
        formatted_value = str(value)

    if override_value is _UNDEFINED or override_value == value:
        return formatted_value

    formatted_override_value = format_settings_value(override_value)
    return f"{formatted_override_value} [default={formatted_value}]"
