import time
from decimal import Decimal
from typing import Annotated

import typer
from rich.live import Live
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table

from portfolio_tracker.application.portfolio import (
    BuildPortfolioSnapshotQuery,
    GetCashBalancesQuery,
    ViewPortfolioSnapshotQuery,
)
from portfolio_tracker.application.shared.service import QueryOptions
from portfolio_tracker.application.views import (
    CashBalanceRowView,
    PositionRowView,
)
from portfolio_tracker.domain.instrument import AssetClass, InstrumentType
from portfolio_tracker.domain.portfolio import ScopeType
from portfolio_tracker.domain.portfolio.position import AccountingMethod
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.presentation.desktop.cli.console import console
from portfolio_tracker.presentation.desktop.cli.context import CliContext
from portfolio_tracker.presentation.desktop.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.desktop.cli.input import (
    FilterInput,
    position_filter_input,
    resolve_filter_inputs,
    resolve_optional_input,
)
from portfolio_tracker.presentation.desktop.cli.parameters import multi_value_option
from portfolio_tracker.presentation.desktop.cli.parsers import (
    date_parser,
    enum_parser,
    money_parser,
    parse_sort_column,
)
from portfolio_tracker.presentation.shared.tables import get_table_spec
from portfolio_tracker.presentation.desktop.cli.table import TableRenderer, display_table

overview_app = GuardedTyper()


@overview_app.command(name="cash-balance")
def list_cash_balance(
    ctx: typer.Context,
    scope: Annotated[ScopeType | None, typer.Option(case_sensitive=False)] = None,
    reporting_currency: Annotated[
        Currency | None, typer.Option("--currency", case_sensitive=False)
    ] = None,
    as_of: Annotated[str | None, typer.Option()] = None,
    connection_id: Annotated[str | None, typer.Option()] = None,
    account_id: Annotated[str | None, typer.Option()] = None,
    active_columns: Annotated[list[str] | None, multi_value_option("--column")] = None,
    sort_columns: Annotated[list[str] | None, multi_value_option("--sort")] = None,
) -> None:
    context: CliContext = ctx.obj
    settings = context.settings
    user_id = context.user_id
    query_service = context.container.portfolio_query_service

    scope = scope or settings.application.consolidation_scope_type
    reporting_currency = reporting_currency or settings.application.reporting_currency
    resolved_as_of = resolve_optional_input("--as-of", as_of, value_parser=date_parser)
    filter_ = resolve_filter_inputs(
        [
            FilterInput(
                parameter="--connection-id",
                value=connection_id,
                item_class=CashBalanceRowView,
                field_path="scope.connection_id",
            ),
            FilterInput(
                parameter="--account-id",
                value=account_id,
                item_class=CashBalanceRowView,
                field_path="scope.account_id",
            ),
        ]
    )

    table_spec = get_table_spec(CashBalanceRowView)
    sort_columns = (
        sort_columns or settings.display.cli.tables[table_spec.name].sort_columns
    )
    sorts = tuple(
        parse_sort_column(sort_column, CashBalanceRowView)
        for sort_column in sort_columns
    )

    balances = query_service.get_cash_balances(
        user_id,
        query=GetCashBalancesQuery(
            build=BuildPortfolioSnapshotQuery(
                reporting_currency=reporting_currency,
                as_of=resolved_as_of,
                accounting_method=settings.application.accounting_method,
            ),
            view=ViewPortfolioSnapshotQuery(
                scope_type=scope,
                options=QueryOptions(
                    filter=filter_,
                    sorts=sorts,
                ),
            )
        ),
    )

    display_table(
        CashBalanceRowView, balances, settings.display.cli, columns=active_columns
    )


@overview_app.command(name="positions")
def list_positions(
    ctx: typer.Context,
    scope: Annotated[ScopeType | None, typer.Option(case_sensitive=False)] = None,
    reporting_currency: Annotated[Currency | None, typer.Option("--currency", case_sensitive=False)] = None,
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
    live: Annotated[bool, typer.Option()] = False,
) -> None:
    context: CliContext = ctx.obj
    settings = context.settings
    user_id = context.user_id
    query_service = context.container.portfolio_query_service

    scope = scope or settings.application.consolidation_scope_type
    reporting_currency = reporting_currency or settings.application.reporting_currency
    reporting_currency_money_parser = money_parser(reporting_currency)
    resolved_as_of = resolve_optional_input("--as-of", as_of, value_parser=date_parser)
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

    table_spec = get_table_spec(PositionRowView)
    table_settings = settings.display.cli.tables[table_spec.name]
    active_columns = active_columns or table_settings.active_columns
    sort_columns = sort_columns or table_settings.sort_columns
    sorts = tuple(
        parse_sort_column(sort_column, PositionRowView) for sort_column in sort_columns
    )
    title = f"{table_spec.title} (Live)" if live else table_spec.title

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(pulse_style="blue"),
        transient=True,
    ) as progress:
        progress.add_task("Processing...", total=None)
        snapshot = query_service.build_snapshot(
            user_id,
            query=BuildPortfolioSnapshotQuery(
                reporting_currency=reporting_currency,
                as_of=resolved_as_of,
                accounting_method=resolved_accounting_method,
            ),
        )

    query = ViewPortfolioSnapshotQuery(
        scope_type=scope,
        options=QueryOptions(
            filter=resolved_filter,
            sorts=sorts,
        ),
    )
    renderer = TableRenderer()
    
    def render_table() -> Table:
        result = query_service.positions_from_snapshot(snapshot, query)
        return renderer.render(
            table_spec,
            result.positions,
            settings.display.cli,
            title=title,
            columns=active_columns,
            total_view=result.totals,
        )

    if not live:
        console.print(render_table())
        return

    with Live(console=console, auto_refresh=False) as live_display:
        while True:
            live_display.update(render_table(), refresh=True)
            time.sleep(30)
