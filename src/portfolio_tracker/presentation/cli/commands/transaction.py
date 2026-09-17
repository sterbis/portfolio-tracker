from decimal import Decimal
from typing import Annotated, Any

import typer

from portfolio_tracker.application.transaction import (
    CreateTransactionCommand,
    GetTransactionsQuery,
    TransactionPayloadDto,
    UpdateTransactionCommand,
)
from portfolio_tracker.application.views import (
    MoneyView,
    TransactionView,
    TransactionTotalView,
)
from portfolio_tracker.domain.instrument import AssetClass, InstrumentType
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.domain.transaction import TransactionType
from portfolio_tracker.presentation.cli.console import console
from portfolio_tracker.presentation.cli.context import (
    get_container,
    get_environment,
    get_logged_in_user_id,
    get_settings,
)
from portfolio_tracker.presentation.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.cli.input import (
    Input,
    optional_prompt_datetime_input,
    optional_prompt_decimal_input,
    optional_prompt_enum_input,
    optional_prompt_money_input,
    optional_prompt_str_input,
    required_datetime_input,
    required_decimal_input,
    required_enum_input,
    required_money_input,
    required_str_input,
    resolve_filter_inputs,
    resolve_input,
    resolve_inputs,
    transaction_filter_input,
)
from portfolio_tracker.presentation.cli.parameters import multi_value_option
from portfolio_tracker.presentation.cli.parsers import (
    datetime_parser,
    enum_parser,
    money_parser,
    parse_sort_column,
)
from portfolio_tracker.presentation.cli.ui.tables import get_view_table

transaction_app = GuardedTyper()


@transaction_app.command(name="list")
def list_transactions(
    ctx: typer.Context,
    institution_account_ids: Annotated[
        list[str] | None, multi_value_option("--institution_account_id")
    ] = None,
    asset_account_ids: Annotated[
        list[str] | None, multi_value_option("--asset_account_id")
    ] = None,
    currency: Annotated[Currency | None, typer.Option(case_sensitive=False)] = None,
    executed_at: Annotated[str | None, typer.Option()] = None,
    type_: Annotated[str | None, typer.Option()] = None,
    quantity: Annotated[str | None, typer.Option()] = None,
    price: Annotated[str | None, typer.Option()] = None,
    fee: Annotated[str | None, typer.Option()] = None,
    tax: Annotated[str | None, typer.Option()] = None,
    cash_impact: Annotated[str | None, typer.Option()] = None,
    instrument_type: Annotated[str | None, typer.Option()] = None,
    instrument_asset_class: Annotated[str | None, typer.Option()] = None,
    instrument_symbol: Annotated[str | None, typer.Option()] = None,
    instrument_name: Annotated[str | None, typer.Option()] = None,
    active_columns: Annotated[list[str] | None, multi_value_option("--column")] = None,
    sort_columns: Annotated[list[str] | None, multi_value_option("--sort")] = None,
    limit: Annotated[int | None, typer.Option()] = None,
    offset: Annotated[int | None, typer.Option()] = None,
) -> None:
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)
    settings = get_settings(ctx, user_id)

    reporting_currency = currency or settings.application.reporting_currency
    reporting_currency_money_parser = money_parser(reporting_currency)

    filter_inputs = [
        transaction_filter_input(
            "--executed-at", executed_at, "executed_at", datetime_parser
        ),
        transaction_filter_input("--type", type_, "type", enum_parser(TransactionType)),
        transaction_filter_input("--quantity", quantity, "quantity", Decimal),
        transaction_filter_input(
            "--price", price, "price.reporting", reporting_currency_money_parser
        ),
        transaction_filter_input(
            "--fee", fee, "fee.reporting", reporting_currency_money_parser
        ),
        transaction_filter_input(
            "--tax", tax, "tax.reporting", reporting_currency_money_parser
        ),
        transaction_filter_input(
            "--cash-impact",
            cash_impact,
            "cash_impact.reporting",
            reporting_currency_money_parser,
        ),
        transaction_filter_input(
            "--instrument-type",
            instrument_type,
            "instrument.type",
            enum_parser(InstrumentType),
        ),
        transaction_filter_input(
            "--instrument-asset-class",
            instrument_asset_class,
            "instrument.asset_class",
            enum_parser(AssetClass),
        ),
        transaction_filter_input(
            "--instrument-symbol",
            instrument_symbol,
            "instrument.symbol",
            lambda value: value.upper(),
        ),
        transaction_filter_input(
            "--instrument-name", instrument_name, "instrument.name"
        ),
    ]
    filter_ = resolve_filter_inputs(filter_inputs)

    transaction_table = get_view_table(TransactionView)

    table_settings = settings.display.cli.tables[transaction_table.name]
    sort_columns = sort_columns or table_settings.sort_columns
    active_columns = active_columns or table_settings.active_columns

    sorts = [
        parse_sort_column(sort_column, TransactionView) for sort_column in sort_columns
    ]

    query = GetTransactionsQuery(
        institution_account_ids=(
            set(institution_account_ids) if institution_account_ids else set()
        ),
        asset_account_ids=set(asset_account_ids) if asset_account_ids else set(),
        reporting_currency=reporting_currency,
        filter=filter_,
        sorts=sorts,
        limit=limit,
        offset=offset,
    )

    views = container.transaction_query_service.get_transactions(user_id, query)
    total_view = TransactionTotalView.from_views(views, reporting_currency)

    rendered_table = transaction_table.render(
        views,
        settings.display.cli,
        active_columns=active_columns,
        total_view=total_view,
    )
    console.print(rendered_table)


@transaction_app.command(name="add")
def add_transaction(
    ctx: typer.Context,
    asset_account_id: Annotated[str | None, typer.Option()] = None,
    correlation_id: Annotated[str | None, typer.Option()] = None,
    executed_at: Annotated[str | None, typer.Option()] = None,
    type_: Annotated[str | None, typer.Option()] = None,
    instrument_id: Annotated[str | None, typer.Option()] = None,
    quantity: Annotated[str | None, typer.Option()] = None,
    price: Annotated[str | None, typer.Option()] = None,
    fee: Annotated[str | None, typer.Option()] = None,
    tax: Annotated[str | None, typer.Option()] = None,
    cash_impact: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)
    settings = get_settings(ctx, user_id)

    reporting_curreny = settings.application.reporting_currency
    zero_money = MoneyView(amount=Decimal("0"), currency=reporting_curreny)

    inputs: list[Input[Any, Any]] = [
        required_str_input("--asset-account-id", asset_account_id),
        optional_prompt_str_input("--correlation-id", correlation_id),
        required_datetime_input("--executed-at", executed_at),
        required_enum_input("--type", type_, TransactionType),
        optional_prompt_str_input("--instrument-id", instrument_id),
        required_decimal_input("--quantity", quantity),
        required_money_input("--price", price, default_value=zero_money),
        required_money_input("--fee", fee, default_value=zero_money),
        required_money_input("--tax", tax, default_value=zero_money),
        required_money_input("--cash_impact", cash_impact, default_value=zero_money),
    ]
    values = resolve_inputs(environment, inputs)

    command = CreateTransactionCommand(
        payload=TransactionPayloadDto(
            asset_account_id=values["--asset-account-id"],
            correlation_id=values["--correlation-id"],
            executed_at=values["--executed-at"],
            type=values["--type"],
            instrument_id=values["--instrument-id"],
            quantity=values["--quantity"],
            price=values["--price"],
            fee=values["--fee"],
            tax=values["--tax"],
            cash_impact=values["--cash-impact"],
        )
    )

    transaction_id = container.transaction_command_service.create_transaction(
        user_id, command
    )
    console.print(f"Transaction '{transaction_id}' successfully added.")


@transaction_app.command(name="edit")
def edit_transaction(
    ctx: typer.Context,
    transaction_id: Annotated[str | None, typer.Option()] = None,
    asset_account_id: Annotated[str | None, typer.Option()] = None,
    correlation_id: Annotated[str | None, typer.Option()] = None,
    executed_at: Annotated[str | None, typer.Option()] = None,
    type_: Annotated[str | None, typer.Option()] = None,
    instrument_id: Annotated[str | None, typer.Option()] = None,
    quantity: Annotated[str | None, typer.Option()] = None,
    price: Annotated[str | None, typer.Option()] = None,
    fee: Annotated[str | None, typer.Option()] = None,
    tax: Annotated[str | None, typer.Option()] = None,
    cash_impact: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    resolved_transaction_id = resolve_input(
        "--transaction-id", transaction_id, environment
    )
    transaction = container.transaction_query_service.get_transaction(
        user_id, resolved_transaction_id
    )

    inputs: list[Input[Any, Any]] = [
        optional_prompt_str_input(
            "--asset-account-id",
            asset_account_id,
            default_value=transaction.asset_account_id,
        ),
        optional_prompt_str_input(
            "--correlation-id", correlation_id, default_value=transaction.correlation_id
        ),
        optional_prompt_datetime_input(
            "--executed-at", executed_at, default_value=transaction.executed_at
        ),
        optional_prompt_enum_input(
            "--type", type_, TransactionType, default_value=transaction.type
        ),
        optional_prompt_str_input(
            "--instrument-id", instrument_id, default_value=transaction.instrument_id
        ),
        optional_prompt_decimal_input(
            "--quantity", quantity, default_value=transaction.quantity
        ),
        optional_prompt_money_input("--price", price, default_value=transaction.price),
        optional_prompt_money_input("--fee", fee, default_value=transaction.fee),
        optional_prompt_money_input("--tax", tax, default_value=transaction.tax),
        optional_prompt_money_input(
            "--cash_impact", cash_impact, default_value=transaction.cash_impact
        ),
    ]
    values = resolve_inputs(environment, inputs)

    command = UpdateTransactionCommand(
        transaction_id=resolved_transaction_id,
        payload=TransactionPayloadDto(
            asset_account_id=values["--asset-account-id"],
            correlation_id=values["--correlation-id"],
            executed_at=values["--executed-at"],
            type=values["--type"],
            instrument_id=values["--instrument-id"],
            quantity=values["--quantity"],
            price=values["--price"],
            fee=values["--fee"],
            tax=values["--tax"],
            cash_impact=values["--cash-impact"],
        ),
    )

    container.transaction_command_service.update_transaction(user_id, command)
    console.print(f"Transaction '{resolved_transaction_id}' successfully updated.")


@transaction_app.command(name="remove")
def remove_transaction(
    ctx: typer.Context,
    transaction_id: Annotated[str | None, typer.Option()] = None,
) -> None:
    environment = get_environment(ctx)
    container = get_container(ctx)
    user_id = get_logged_in_user_id(ctx)

    resolved_transaction_id = resolve_input(
        "--transaction-id", transaction_id, environment
    )
    transaction = container.transaction_query_service.get_transaction(
        user_id, resolved_transaction_id
    )

    if environment.is_interactive:
        remove = typer.confirm(
            f"Are you sure you want to remove transaction ({transaction.id})?",
            default=False,
        )
        if not remove:
            console.print("Operation cancelled.")
            return

    container.transaction_command_service.delete_transaction(user_id, transaction.id)

    console.print(f"Transaction ({transaction.id}) successfully removed.")
