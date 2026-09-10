from dataclasses import dataclass


@dataclass(frozen=True)
class CliEnvironment:
    is_interactive: bool
