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
            "institution_connection": TableDisplaySettings(
                active_columns=[
                    "institution_name",
                    "connection_id",
                    "connection_name",
                    "sync_from",
                    "credentials",
                ],
                sort_columns=["institution_name", "connection_name"],
            ),
            "transaction": TableDisplaySettings(
                active_columns=[
                    "account_name",
                    "executed_at",
                    "type",
                    "instrument_symbol",
                    "quantity",
                    "price",
                    "fee",
                    "tax",
                    "cash_impact",
                ],
                sort_columns=["account_name", "executed_at"],
            ),
            "cash_balance": TableDisplaySettings(
                active_columns=[
                    "account_name",
                    "amount",
                    "currency",
                ],
                sort_columns=["account_name", "currency"],
            ),
            "position": TableDisplaySettings(
                active_columns=[
                    "instrument_type",
                    "instrument_name",
                    "instrument_symbol",
                    "quantity",
                    "cost_basis",
                    "market_value",
                    "unrealized_pnl",
                    "unrealized_pnl_percent",
                    "average_price",
                    "market_price",
                ],
                sort_columns=["instrument_name"],
            ),
        }
    )
