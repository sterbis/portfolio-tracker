import itertools
from typing import Any, Callable

import typer

from .parsers import parse_multi_value


def multi_value_option(
    *param_decls: str,
    separator: str = ",",
    value_parser: Callable[[str], Any] | None = None,
    **option_kwargs: Any,
) -> Any:
    def parser(value: str) -> list[str]:
        return parse_multi_value(value, separator=separator)

    def callback(
        ctx: typer.Context, value: tuple[list[str], ...] | None
    ) -> list[Any] | None:
        if ctx.resilient_parsing or not value:
            return None

        items = list(itertools.chain.from_iterable(value))
        if value_parser is None:
            return items
        
        return [value_parser(item) for item in items]

    return typer.Option(*param_decls, parser=parser, callback=callback, **option_kwargs)
