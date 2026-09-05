from dataclasses import dataclass, field


@dataclass(frozen=True)
class TableSettings:
    displayed_columns: list[str]
    sort_columns: list[str]


@dataclass(frozen=True)
class CliDisplaySettings:
    tables: dict[str, TableSettings] = field(
        default_factory=lambda: {
            "transaction": TableSettings(
                displayed_columns=["account", "executed_at", "type", "symbol", "price"],
                sort_columns=["account", "executed_at"],
            )
        }
    )
