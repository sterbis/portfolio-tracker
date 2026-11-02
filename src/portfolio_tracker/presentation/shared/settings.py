from dataclasses import dataclass

from .tables import get_table_spec_by_name


@dataclass(frozen=True, kw_only=True)
class TableDisplaySettings:
    active_columns: list[str]
    sort_columns: list[str]


@dataclass(frozen=True, kw_only=True)
class DisplaySettings:
    date_format: str
    time_format: str
    none_value: str
    quantity_decimal_places: int
    percent_decimal_places: int
    money_decimal_places: int
    tables: dict[str, TableDisplaySettings]

    def __post_init__(self) -> None:
        for table_name, table_settings in self.tables.items():
            table_spec = get_table_spec_by_name(table_name)
            column_names = table_settings.active_columns + [
                column.lstrip("+-") for column in table_settings.sort_columns
            ]
            invalid_column_names = [
                column_name
                for column_name in column_names
                if column_name not in table_spec.columns
            ]
            if invalid_column_names:
                raise ValueError("...")
