from rich.console import Console
from rich.theme import Theme

_THEME = Theme(
    {
        "profit": "green",
        "loss": "red",
    }
)

console = Console(theme=_THEME)
error_console = Console(stderr=True)
