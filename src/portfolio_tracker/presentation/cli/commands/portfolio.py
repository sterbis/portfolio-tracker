from decimal import Decimal
from typing import Annotated

import typer

from portfolio_tracker.application.portfolio import GetPortfoliosQuery
from portfolio_tracker.domain.instrument import AssetClass, InstrumentType
from portfolio_tracker.domain.portfolio import ConsolidationScope
from portfolio_tracker.domain.shared import Currency
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
from portfolio_tracker.presentation.cli.parsers import enum_parser, money_parser

portfolio_app = GuardedTyper()


@portfolio_app.command(name="cash-balance")
def cash_balance(
    ctx: typer.Context,
    institution_account_id: Annotated[list[str] | None, multi_value_option()] = None,
    asset_account_id: Annotated[list[str] | None, multi_value_option()] = None,
    scope: Annotated[
        ConsolidationScope | None, typer.Option(case_sensitive=False)
    ] = None,
    currency: Annotated[Currency | None, typer.Option(case_sensitive=False)] = None,
) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)
    settings = get_settings(ctx)

    institution_account_ids = (
        set(institution_account_id) if institution_account_id else set()
    )
    asset_account_ids = set(asset_account_id) if asset_account_id else set()

    scope = scope or settings.application.consolidation_scope
    reporting_currency = currency or settings.application.reporting_currency

    query = GetPortfoliosQuery(
        institution_account_ids=institution_account_ids,
        asset_account_ids=asset_account_ids,
        scope=scope,
        reporting_currency=reporting_currency,
    )

    _ = container.portfolio_query_service.get_valued_portfolios(user_id, query)


@portfolio_app.command(name="positions")
def positions(
    ctx: typer.Context,
    institution_account_id: Annotated[list[str] | None, multi_value_option()] = None,
    asset_account_id: Annotated[list[str] | None, multi_value_option()] = None,
    scope: Annotated[
        ConsolidationScope | None, typer.Option(case_sensitive=False)
    ] = None,
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
) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)
    settings = get_settings(ctx)

    institution_account_ids = (
        set(institution_account_id) if institution_account_id else set()
    )
    asset_account_ids = set(asset_account_id) if asset_account_id else set()

    scope = scope or settings.application.consolidation_scope
    reporting_currency = currency or settings.application.reporting_currency
    reporting_currency_money_parser = money_parser(reporting_currency)

    filter_inputs = [
        position_filter_input(
            "--type",
            type_,
            "instrument.type",
            enum_parser(InstrumentType),
        ),
        position_filter_input(
            "--asset-class",
            asset_class,
            "instrument.asset_class",
            enum_parser(AssetClass),
        ),
        position_filter_input(
            "--symbol",
            symbol,
            "instrument.symbol",
            lambda value: value.upper(),
        ),
        position_filter_input("--name", name, "instrument.name"),
        position_filter_input("--quantity", quantity, "quantity", Decimal),
        position_filter_input(
            "--cost-basis",
            cost_basis,
            "cost_basis.reporting",
            reporting_currency_money_parser,
        ),
        position_filter_input(
            "--market-value",
            market_value,
            "market_value.reporting",
            reporting_currency_money_parser,
        ),
        position_filter_input(
            "--unrealized-pnl",
            unrealized_pnl,
            "unrealized_pnl.reporting",
            reporting_currency_money_parser,
        ),
        position_filter_input(
            "--unrealized-pnl-percent",
            unrealized_pnl_percent,
            "unrealized_pnl_percent",
            Decimal,
        ),
    ]
    filter_ = resolve_filter_inputs(filter_inputs)

    query = GetPortfoliosQuery(
        institution_account_ids=institution_account_ids,
        asset_account_ids=asset_account_ids,
        scope=scope,
        reporting_currency=reporting_currency,
        filter=filter_,
    )

    _ = container.portfolio_query_service.get_valued_portfolios(user_id, query)
