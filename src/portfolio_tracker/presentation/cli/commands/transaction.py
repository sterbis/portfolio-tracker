from decimal import Decimal
from typing import Annotated

import typer
from filterutils import Filter, FilterTree

from portfolio_tracker.application.transaction import (
    GetTransactionsQuery,
    TransactionQueryService,
)
from portfolio_tracker.bootstrap import ApplicationContext
from portfolio_tracker.domain.instrument import AssetClass, Instrument, InstrumentType
from portfolio_tracker.domain.transaction import Transaction, TransactionType
from portfolio_tracker.presentation.cli.parameters import (
    FilterParameterType,
)
from portfolio_tracker.presentation.cli.parsers import (
    parse_datetime_parameter,
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
                Transaction, "executed_at", parse_datetime_parameter
            )
        ),
    ] = None,
    type_: Annotated[
        Filter | None,
        typer.Option(type=FilterParameterType(Transaction, "type", TransactionType)),
    ] = None,
    quantity: Annotated[
        Filter | None,
        typer.Option(type=FilterParameterType(Transaction, "quantity", Decimal)),
    ] = None,
    price: Annotated[
        Filter | None,
        typer.Option(type=FilterParameterType(Transaction, "price", Decimal)),
    ] = None,
    instrument_type: Annotated[
        Filter | None,
        typer.Option(type=FilterParameterType(Instrument, "type", InstrumentType)),
    ] = None,
    asset_class: Annotated[
        Filter | None,
        typer.Option(type=FilterParameterType(Instrument, "asset_class", AssetClass)),
    ] = None,
    symbol: Annotated[
        Filter | None, typer.Option(type=FilterParameterType(Instrument, "symbol"))
    ] = None,
    name: Annotated[
        Filter | None, typer.Option(type=FilterParameterType(Instrument, "name"))
    ] = None,
    limit: Annotated[int | None, typer.Option()] = None,
    offset: Annotated[int | None, typer.Option()] = None,
    sort: Annotated[list[str] | None, typer.Option()] = None,
) -> None:
    account_ids = set(parse_list_parameter(account_id))
    asset_account_ids = set(parse_list_parameter(asset_account_id))

    _ = parse_list_parameter(sort, converter=parse_sort_parameter)

    filter_ = FilterTree()
    for option in (executed_at, type_):
        if option:
            filter_.add_child(option)

    context: ApplicationContext = ctx.obj
    service = context.get(TransactionQueryService)

    query = GetTransactionsQuery(
        institution_account_ids=account_ids,
        asset_account_ids=asset_account_ids,
        filter=filter_,
        limit=limit,
        offset=offset,
        reporting_currency=context.DEFAULT_REPORTING_CURRENCY,
    )

    _ = service.get_transactions(context.active_user_id, query)
