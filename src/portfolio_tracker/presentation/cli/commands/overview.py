import time
from decimal import Decimal
from typing import Annotated

import typer
from rich.live import Live

from portfolio_tracker.application.portfolio import (
    GetPortfoliosQuery,
    BuildPortfoliosQuery,
    GetCashBalancesQuery,
)
from portfolio_tracker.application.views import (
    CashBalanceRowView,
    PositionRowTotalView,
    PositionRowView,
)
from portfolio_tracker.domain.instrument import AssetClass, InstrumentType
from portfolio_tracker.domain.portfolio import ScopeType
from portfolio_tracker.domain.portfolio.position import AccountingMethod
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.presentation.cli.console import console
from portfolio_tracker.presentation.cli.context import (
    get_container,
    get_logged_in_user_id,
    get_settings,
)
from portfolio_tracker.presentation.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.cli.input import (
    FilterInput,
    position_filter_input,
    resolve_filter_inputs,
    resolve_optional_input,
)
from portfolio_tracker.presentation.cli.parameters import multi_value_option
from portfolio_tracker.presentation.cli.parsers import (
    date_parser,
    enum_parser,
    money_parser,
    parse_sort_column,
)
from portfolio_tracker.presentation.cli.ui.tables import get_view_table

overview_app = GuardedTyper()


@overview_app.command(name="cash-balance")
def list_cash_balance(
    ctx: typer.Context,
    scope: Annotated[ScopeType | None, typer.Option(case_sensitive=False)] = None,
    reporting_currency: Annotated[
        Currency | None, typer.Option("--currency", case_sensitive=False)
    ] = None,
    connection_id: Annotated[str | None, typer.Option()] = None,
    account_id: Annotated[str | None, typer.Option()] = None,
    active_columns: Annotated[list[str] | None, multi_value_option("--column")] = None,
    sort_columns: Annotated[list[str] | None, multi_value_option("--sort")] = None,
) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)
    settings = get_settings(ctx)

    scope = scope or settings.application.consolidation_scope
    reporting_currency = reporting_currency or settings.application.reporting_currency
    filter_ = resolve_filter_inputs(
        [
            FilterInput(
                parameter="--connection-id",
                value=connection_id,
                item_type=CashBalanceRowView,
                field="scope.connection_id",
            ),
            FilterInput(
                parameter="--account-id",
                value=account_id,
                item_type=CashBalanceRowView,
                field="scope.account_id",
            ),
        ]
    )

    table = get_view_table(CashBalanceRowView)
    table_settings = settings.display.cli.tables[table.name]
    sort_columns = sort_columns or table_settings.sort_columns
    active_columns = active_columns or table_settings.active_columns

    sorts = [
        parse_sort_column(sort_column, CashBalanceRowView)
        for sort_column in sort_columns
    ]

    balances = container.portfolio_query_service.get_cash_balances(
        user_id,
        query=GetCashBalancesQuery(
            reporting_currency=reporting_currency,
            scope=scope,
            filter=filter_,
            sorts=sorts,
        ),
    )
    rendered_table = table.render(
        balances,
        settings.display.cli,
        active_columns=active_columns,
    )
    console.print(rendered_table)


@overview_app.command(name="positions")
def list_positions(
    ctx: typer.Context,
    scope: Annotated[ScopeType | None, typer.Option(case_sensitive=False)] = None,
    reporting_currency: Annotated[
        Currency | None, typer.Option("--currency", case_sensitive=False)
    ] = None,
    as_of: Annotated[str | None, typer.Option()] = None,
    accounting_method: Annotated[AccountingMethod | None, typer.Option()] = None,
    connection_id: Annotated[str | None, typer.Option()] = None,
    account_id: Annotated[str | None, typer.Option()] = None,
    instrument_type: Annotated[str | None, typer.Option()] = None,
    instrument_asset_class: Annotated[str | None, typer.Option()] = None,
    instrument_symbol: Annotated[str | None, typer.Option()] = None,
    instrument_name: Annotated[str | None, typer.Option()] = None,
    quantity: Annotated[str | None, typer.Option()] = None,
    cost_basis: Annotated[str | None, typer.Option()] = None,
    market_value: Annotated[str | None, typer.Option()] = None,
    unrealized_pnl: Annotated[str | None, typer.Option()] = None,
    unrealized_pnl_percent: Annotated[str | None, typer.Option()] = None,
    active_columns: Annotated[list[str] | None, multi_value_option("--column")] = None,
    sort_columns: Annotated[list[str] | None, multi_value_option("--sort")] = None,
) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)
    settings = get_settings(ctx)

    scope = scope or settings.application.consolidation_scope
    reporting_currency = reporting_currency or settings.application.reporting_currency
    reporting_currency_money_parser = money_parser(reporting_currency)
    resolved_as_of = resolve_optional_input("as-of", as_of, value_parser=date_parser)
    resolved_accounting_method = (
        accounting_method or settings.application.accounting_method
    )

    filter_inputs = [
        position_filter_input(
            "--connection-id",
            connection_id,
            "position.scope.connection_id",
        ),
        position_filter_input(
            "--account-id",
            account_id,
            "position.scope.account_id",
        ),
        position_filter_input(
            "--type",
            instrument_type,
            "position.instrument.type",
            enum_parser(InstrumentType),
        ),
        position_filter_input(
            "--asset-class",
            instrument_asset_class,
            "position.instrument.asset_class",
            enum_parser(AssetClass),
        ),
        position_filter_input(
            "--symbol",
            instrument_symbol,
            "position.instrument.symbol",
            lambda value: value.upper(),
        ),
        position_filter_input("--name", instrument_name, "position.instrument.name"),
        position_filter_input("--quantity", quantity, "position.quantity", Decimal),
        position_filter_input(
            "--cost-basis",
            cost_basis,
            "position.cost_basis.reporting",
            reporting_currency_money_parser,
        ),
        position_filter_input(
            "--market-value",
            market_value,
            "valuation.market_value.reporting",
            reporting_currency_money_parser,
        ),
        position_filter_input(
            "--unrealized-pnl",
            unrealized_pnl,
            "valuation.unrealized_pnl.reporting",
            reporting_currency_money_parser,
        ),
        position_filter_input(
            "--unrealized-pnl-percent",
            unrealized_pnl_percent,
            "valuation.reporting_unrealized_pnl_percent",
            Decimal,
        ),
    ]
    resolved_filter = resolve_filter_inputs(filter_inputs)

    portfolios_snapshot = container.portfolio_query_service.build_portfolios(
        user_id,
        query=BuildPortfoliosQuery(
            reporting_currency=reporting_currency,
            as_of=resolved_as_of,
            accounting_method=resolved_accounting_method,
        ),
    )

    table = get_view_table(PositionRowView)
    table_settings = settings.display.cli.tables[table.name]
    sort_columns = sort_columns or table_settings.sort_columns
    active_columns = active_columns or table_settings.active_columns
    sorts = [
        parse_sort_column(sort_column, PositionRowView) for sort_column in sort_columns
    ]

    query = GetPortfoliosQuery(
        scope=scope,
        filter=resolved_filter,
        sorts=sorts,
        portfolios_snapshot=portfolios_snapshot,
    )
    update_count = 0

    with Live(console=console, auto_refresh=False) as live:
        while True:
            positions = container.portfolio_query_service.get_positions(user_id, query)
            position_total = PositionRowTotalView.from_views(
                positions, reporting_currency
            )
            rendered_table = table.render(
                positions,
                settings.display.cli,
                title=f"Positions (update {update_count})",
                active_columns=active_columns,
                total_view=position_total,
            )
            live.update(rendered_table, refresh=True)
            update_count += 1
            time.sleep(5)
