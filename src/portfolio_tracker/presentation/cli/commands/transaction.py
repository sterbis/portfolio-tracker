from decimal import Decimal
from typing import Annotated

import typer
from filterutils import Filter

from portfolio_tracker.application.transaction import (
    GetTransactionsQuery,
    TransactionQueryService,
)
from portfolio_tracker.application.views import TransactionView
from portfolio_tracker.bootstrap_desktop import Container
from portfolio_tracker.domain.instrument import AssetClass, InstrumentType
from portfolio_tracker.domain.transaction import TransactionType
from portfolio_tracker.presentation.cli.parameters import (
    FilterParameterType, MoneyFilterParameterType
)
from portfolio_tracker.presentation.cli.parsers import (
    build_filter,
    parse_datetime,
    parse_list_parameter,
    parse_sort_parameter,
)

transaction_app = typer.Typer()


@transaction_app.command(name="list")
def list_transactions(
    ctx: typer.Context,
    account_id: Annotated[list[str] | None, typer.Option()] = None,
    asset_account_id: Annotated[list[str] | None, typer.Option()] = None,
    executed_at: Annotated[
        Filter | None,
        typer.Option(
            type=FilterParameterType(
                TransactionView, "executed_at", parse_datetime
            )
        ),
    ] = None,
    type_: Annotated[
        Filter | None,
        typer.Option(type=FilterParameterType(TransactionView, "type", TransactionType)),
    ] = None,
    quantity: Annotated[
        Filter | None,
        typer.Option(type=FilterParameterType(TransactionView, "quantity", Decimal)),
    ] = None,
    price: Annotated[
        Filter | None,
        typer.Option(type=MoneyFilterParameterType(TransactionView, "price")),
    ] = None,
    fee: Annotated[
        Filter | None,
        typer.Option(type=MoneyFilterParameterType(TransactionView, "fee")),
    ] = None,
    tax: Annotated[
        Filter | None,
        typer.Option(type=MoneyFilterParameterType(TransactionView, "tax")),
    ] = None,
    cash_impact: Annotated[
        Filter | None,
        typer.Option(type=MoneyFilterParameterType(TransactionView, "cash_impact")),
    ] = None,
    instrument_type: Annotated[
        Filter | None,
        typer.Option(type=FilterParameterType(TransactionView, "instrument.type", InstrumentType)),
    ] = None,
    instrument_asset_class: Annotated[
        Filter | None,
        typer.Option(type=FilterParameterType(TransactionView, "instrument.asset_class", AssetClass)),
    ] = None,
    instrument_symbol: Annotated[
        Filter | None, typer.Option(type=FilterParameterType(TransactionView, "instrument.symbol"))
    ] = None,
    instrument_name: Annotated[
        Filter | None, typer.Option(type=FilterParameterType(TransactionView, "instrument.name"))
    ] = None,
    sort: Annotated[list[str] | None, typer.Option()] = None,
    limit: Annotated[int | None, typer.Option()] = None,
    offset: Annotated[int | None, typer.Option()] = None,
) -> None:
    account_ids = set(parse_list_parameter(account_id))
    asset_account_ids = set(parse_list_parameter(asset_account_id))

    filter_ = build_filter(
        executed_at,
        type_,
        quantity,
        price,
        fee,
        tax,
        cash_impact,
        instrument_type,
        instrument_asset_class,
        instrument_symbol,
        instrument_name,
    )
    _ = parse_list_parameter(sort, converter=parse_sort_parameter)

    context: Container = ctx.obj
    service = context.get(TransactionQueryService)

    query = GetTransactionsQuery(
        reporting_currency=context.DEFAULT_REPORTING_CURRENCY,
        institution_account_ids=account_ids,
        asset_account_ids=asset_account_ids,
        filter=filter_,
        limit=limit,
        offset=offset,
    )

    _ = service.get_transactions(context.active_user_id, query)
