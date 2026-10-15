from .registry import get_table_spec, get_table_spec_by_name
from .renderer import TableRenderer, display_table

__all__ = [
    "TableRenderer",
    "display_table",
    "get_table_spec",
    "get_table_spec_by_name",
]
