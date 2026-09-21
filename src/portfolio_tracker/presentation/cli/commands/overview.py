from decimal import Decimal
from typing import Annotated

import typer

from portfolio_tracker.application.portfolio import GetPortfoliosQuery
from portfolio_tracker.application.views import CashBalanceRowView, PositionRowView
from portfolio_tracker.domain.instrument import AssetClass, InstrumentType
from portfolio_tracker.domain.portfolio import ScopeType
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.presentation.cli.console import console
from portfolio_tracker.presentation.cli.context import (
    get_container,
    get_logged_in_user_id,
    get_settings,
)
from portfolio_tracker.presentation.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.cli.input import (
    position_filter_input,
    resolve_filter_inputs,
)
from portfolio_tracker.presentation.cli.parameters import multi_value_option
from portfolio_tracker.presentation.cli.parsers import (
    datetime_parser,
    enum_parser,
    money_parser,
    parse_sort_column,
)
from portfolio_tracker.presentation.cli.ui.tables import get_view_table

overview_app = GuardedTyper()


@overview_app.command(name="cash-balance")
def list_cash_balance(
    ctx: typer.Context,
    institution_connection_ids: Annotated[
        list[str] | None, multi_value_option("--institution-connection-id")
    ] = None,
    account_ids: Annotated[list[str] | None, multi_value_option("--account-id")] = None,
    scope: Annotated[ScopeType | None, typer.Option(case_sensitive=False)] = None,
    currency: Annotated[Currency | None, typer.Option(case_sensitive=False)] = None,
    active_columns: Annotated[list[str] | None, multi_value_option("--column")] = None,
    sort_columns: Annotated[list[str] | None, multi_value_option("--sort")] = None,
) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)
    settings = get_settings(ctx)

    scope = scope or settings.application.consolidation_scope
    reporting_currency = currency or settings.application.reporting_currency

    table = get_view_table(CashBalanceRowView)
    table_settings = settings.display.cli.tables[table.name]
    sort_columns = sort_columns or table_settings.sort_columns
    active_columns = active_columns or table_settings.active_columns

    sorts = [
        parse_sort_column(sort_column, CashBalanceRowView)
        for sort_column in sort_columns
    ]

    query = GetPortfoliosQuery(
        institution_connection_ids=(
            set(institution_connection_ids) if institution_connection_ids else set()
        ),
        account_ids=set(account_ids) if account_ids else set(),
        scope=scope,
        reporting_currency=reporting_currency,
        sorts=sorts,
    )

    balances = container.portfolio_query_service.get_cash_balances(user_id, query)
    rendered_table = table.render(
        balances,
        settings.display.cli,
        active_columns=active_columns,
    )
    console.print(rendered_table)


@overview_app.command(name="positions")
def list_positions(
    ctx: typer.Context,
    institution_connection_id: Annotated[list[str] | None, multi_value_option()] = None,
    asset_account_id: Annotated[list[str] | None, multi_value_option()] = None,
    scope: Annotated[ScopeType | None, typer.Option(case_sensitive=False)] = None,
    currency: Annotated[Currency | None, typer.Option(case_sensitive=False)] = None,
    type_: Annotated[str | None, typer.Option()] = None,
    asset_class: Annotated[str | None, typer.Option()] = None,
    symbol: Annotated[str | None, typer.Option()] = None,
    name: Annotated[str | None, typer.Option()] = None,
    quantity: Annotated[str | None, typer.Option()] = None,
    cost_basis: Annotated[str | None, typer.Option()] = None,
    market_value: Annotated[str | None, typer.Option()] = None,
    unrealized_pnl: Annotated[str | None, typer.Option()] = None,
    unrealized_pnl_percent: Annotated[str | None, typer.Option()] = None,
    last_trade_at: Annotated[str | None, typer.Option()] = None,
    active_columns: Annotated[list[str] | None, multi_value_option("--column")] = None,
    sort_columns: Annotated[list[str] | None, multi_value_option("--sort")] = None,
) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)
    settings = get_settings(ctx)

    institution_connection_ids = (
        set(institution_connection_id) if institution_connection_id else set()
    )
    asset_account_ids = set(asset_account_id) if asset_account_id else set()

    scope = scope or settings.application.consolidation_scope
    reporting_currency = currency or settings.application.reporting_currency
    reporting_currency_money_parser = money_parser(reporting_currency)

    filter_inputs = [
        position_filter_input(
            "--type",
            type_,
            "position.instrument.type",
            enum_parser(InstrumentType),
        ),
        position_filter_input(
            "--asset-class",
            asset_class,
            "position.instrument.asset_class",
            enum_parser(AssetClass),
        ),
        position_filter_input(
            "--symbol",
            symbol,
            "position.instrument.symbol",
            lambda value: value.upper(),
        ),
        position_filter_input("--name", name, "position.instrument.name"),
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
        position_filter_input(
            "--last-trade-at",
            last_trade_at,
            "position.last_trade_at",
            datetime_parser,
        ),
    ]
    filter_ = resolve_filter_inputs(filter_inputs)

    table = get_view_table(PositionRowView)
    table_settings = settings.display.cli.tables[table.name]
    sort_columns = sort_columns or table_settings.sort_columns
    active_columns = active_columns or table_settings.active_columns
    sorts = [
        parse_sort_column(sort_column, PositionRowView) for sort_column in sort_columns
    ]

    query = GetPortfoliosQuery(
        institution_connection_ids=institution_connection_ids,
        account_ids=asset_account_ids,
        scope=scope,
        reporting_currency=reporting_currency,
        filter=filter_,
        sorts=sorts,
    )

    positions = container.portfolio_query_service.get_positions(user_id, query)

    rendered_table = table.render(
        positions,
        settings.display.cli,
        active_columns=active_columns,
    )
    console.print(rendered_table)
