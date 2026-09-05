import itertools
from typing import Any, Callable

import typer
from filterutils import Filter, FilterError, FilterExpressionParser

from .parsers import parse_multi_value


def suppress_parser(value: str) -> str:
    return value


def multi_value_option(
    *param_decls: str,
    separator: str = ",",
    **option_kwargs: Any,
) -> Any:
    def parser(value: str) -> list[str]:
        return parse_multi_value(value, separator=separator)

    def callback(
        ctx: typer.Context, value: tuple[list[str], ...] | None
    ) -> list[str] | None:
        if ctx.resilient_parsing or not value:
            return None

        return list(itertools.chain.from_iterable(value))

    return typer.Option(*param_decls, parser=parser, callback=callback, **option_kwargs)


def filter_option(
    *param_decls: str,
    model: type,
    field: str,
    value_parser: Callable[[str], Any] | None = None,
    context_aware_value_parser: Callable[[str, typer.Context], Any] | None = None,
    **option_kwargs: Any,
) -> Any:
    if value_parser is not None and context_aware_value_parser is not None:
        raise TypeError("Pass either value_parser or context_aware_value_parser.")

    def callback(ctx: typer.Context, expression: str | None) -> Filter | None:
        if ctx.resilient_parsing or expression is None:
            return None

        if context_aware_value_parser is not None:
            resolved_parser: Callable[[str], Any] | None = (
                lambda value: context_aware_value_parser(value, ctx)
            )

        else:
            resolved_parser = value_parser

        try:
            return FilterExpressionParser.parse(
                field=field,
                expression=expression,
                item_type=model,
                value_parser=resolved_parser,
            )

        except FilterError as error:
            raise typer.BadParameter(str(error)) from error

    return typer.Option(
        *param_decls, parser=suppress_parser, callback=callback, **option_kwargs
    )
