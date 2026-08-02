from datetime import datetime, date, timezone
from enum import StrEnum
from typing import Any, Callable

import click
from filterutils import Filter, FilterExpressionParser, FilterError

from portfolio_tracker.bootstrap import ApplicationContext

from .parsers import parse_date_parameter, parse_datetime_parameter


class DatetimeParameterType(click.ParamType[datetime]):
    name = "datetime"

    def convert(
        self, value: Any, param: click.Parameter | None, ctx: click.Context | None
    ) -> datetime:
        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time(), timezone.utc)

        date_formats = None
        if ctx:
            context: ApplicationContext = ctx.obj
            date_formats = context.DATE_FORMATS

        try:
            return parse_datetime_parameter(str(value), date_formats)
        except ValueError:
            pass

        if date_formats:
            date_hint = f"[{' | '.join(date_formats)}]"
        else:
            date_hint = "[YYYY-MM-DD]"

        message = (
            f"Invalid datetime format '{value}'. "
            f"Expected date {date_hint} with optional time [HH:MM[:SS][±HH:MM[:SS]]]. "
            "Examples: '2026-06-01', '31/05/2026 14:30:00+02:00', or ISO 8601 format."
        )
        self.fail(message, param, ctx)

    def get_metavar(self, param: click.Parameter, ctx: click.Context) -> str:
        context: ApplicationContext = ctx.obj
        return f"[{'|'.join(context.DATE_FORMATS)}[ HH:MM[:SS][±HH:MM[:SS]]]]"


class DateParameterType(click.ParamType[date]):
    name = "date"

    def convert(
        self, value: Any, param: click.Parameter | None, ctx: click.Context | None
    ) -> date:
        if isinstance(value, date):
            return value

        formats = None
        if ctx:
            context: ApplicationContext = ctx.obj
            formats = context.DATE_FORMATS

        try:
            return parse_date_parameter(str(value), formats)
        except ValueError:
            pass

        if formats:
            mesage = f"Invalid date format '{value}'. Supported formats: {', '.join(formats)} or ISO 8601 format (YYYY-MM-DD)."
        else:
            mesage = f"Invalid date format '{value}'. Expected ISO 8601 format (YYYY-MM-DD)."

        self.fail(mesage, param, ctx)

    def get_metavar(self, param: click.Parameter, ctx: click.Context) -> str:
        context: ApplicationContext = ctx.obj
        return f"[{'|'.join(context.DATE_FORMATS)}]"


class FilterParameterType(click.ParamType[Filter]):
    name = "filter"

    def __init__(self, field: str, value_parser: Callable[[str], Any] | None = None) -> None:
        self._field = field
        self._value_parser = value_parser

    def convert(
        self, value: Any, param: click.Parameter | None, ctx: click.Context | None
    ) -> Filter:
        if isinstance(value, Filter):
            return value

        try:
            return FilterExpressionParser.parse(self._field, str(value), self._value_parser)
        except FilterError as error:
            self.fail(str(error), param, ctx)

    def get_metavar(self, param: click.Parameter, ctx: click.Context) -> str:
        if isinstance(self._value_parser, type) and issubclass(self._value_parser, StrEnum):
            return f"[{'|'.join(value.upper() for value in self._value_parser)}]"

        return f"[{self._field.upper()} EXPRESSION]"
