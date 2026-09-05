from dataclasses import dataclass


@dataclass(frozen=True)
class CliEnvironment:
    interactive: bool
