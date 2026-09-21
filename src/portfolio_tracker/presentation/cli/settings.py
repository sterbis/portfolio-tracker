from dataclasses import dataclass, field


@dataclass(frozen=True)
class TableDisplaySettings:
    active_columns: list[str]
    sort_columns: list[str]


@dataclass(frozen=True)
class CliDisplaySettings:
    date_format: str = "%d/%m/%Y"
    time_format: str = "%H:%M:%S.%f"
    none_value: str = "N/A"
    quantity_decimal_places: int = 4
    percent_decimal_places: int = 2
    money_decimal_places: int = 2
    tables: dict[str, TableDisplaySettings] = field(
        default_factory=lambda: {
            "transaction": TableDisplaySettings(
                active_columns=["account", "executed_at", "type", "symbol", "price"],
                sort_columns=["account", "executed_at"],
            )
        }
    )
