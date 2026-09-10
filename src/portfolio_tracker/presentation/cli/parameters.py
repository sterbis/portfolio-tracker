import itertools
from typing import Any

import typer

from .parsers import parse_multi_value


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
