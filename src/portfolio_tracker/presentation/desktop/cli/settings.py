from portfolio_tracker.settings import DisplaySettings, TableDisplaySettings


CLI_DISPLAY_SETTINGS = DisplaySettings(
    date_format="%d/%m/%Y",
    time_format="%H:%M:%S.%f",
    none_value="N/A",
    quantity_decimal_places=4,
    percent_decimal_places=2,
    money_decimal_places=2,
    tables={
        "institution_connection": TableDisplaySettings(
            active_columns=[
                "connection_id",
                "institution_name",
                "connection_name",
                "sync_from",
                "credentials",
            ],
            sort_columns=["institution_name", "connection_name"],
        ),
        "transaction": TableDisplaySettings(
            active_columns=[
                "transaction_id",
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
                "instrument_name",
                "instrument_symbol",
                "quantity",
                "cost_basis",
                "market_value",
                "invested_capital_weight",
                "unrealized_pnl",
                "unrealized_pnl_percent",
                "average_price",
                "market_price",
            ],
            sort_columns=["instrument_name"],
        ),
    },
)
