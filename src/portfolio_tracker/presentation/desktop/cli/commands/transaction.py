from decimal import Decimal
from typing import Annotated, Any

import typer

from portfolio_tracker.application.shared.service import QueryOptions
from portfolio_tracker.application.transaction import (
    CreateTransactionCommand,
    GetTransactionsQuery,
    TransactionPayloadDto,
    UpdateTransactionCommand,
)
from portfolio_tracker.application.views import (
    MoneyView,
    TransactionTotalView,
    TransactionView,
)
from portfolio_tracker.domain.instrument import AssetClass, InstrumentType
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.domain.transaction import TransactionType
from portfolio_tracker.presentation.desktop.cli.console import console
from portfolio_tracker.presentation.desktop.cli.context import CliContext
from portfolio_tracker.presentation.desktop.cli.guarded_typer import GuardedTyper
from portfolio_tracker.presentation.desktop.cli.input import (
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
from portfolio_tracker.presentation.desktop.cli.parameters import multi_value_option
from portfolio_tracker.presentation.desktop.cli.parsers import (
    datetime_parser,
    enum_parser,
    money_parser,
    parse_sort_column,
)
from portfolio_tracker.presentation.shared.tables import get_table_spec
from portfolio_tracker.presentation.desktop.cli.table import display_table

transaction_app = GuardedTyper()


@transaction_app.command(name="list")
def list_transactions(
    ctx: typer.Context,
    connection_ids: Annotated[
        list[str] | None, multi_value_option("--connection-id")
    ] = None,
    account_ids: Annotated[list[str] | None, multi_value_option("--account-id")] = None,
    reporting_currency: Annotated[Currency | None, typer.Option("--curency", case_sensitive=False)] = None,
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
    context: CliContext = ctx.obj
    settings = context.settings
    user_id = context.user_id
    query_service = context.container.transaction_query_service

    reporting_currency = reporting_currency or settings.application.reporting_currency
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

    table_spec = get_table_spec(TransactionView)
    sort_columns = (
        sort_columns or settings.display.cli.tables[table_spec.name].sort_columns
    )
    sorts = tuple(
        parse_sort_column(sort_column, TransactionView) for sort_column in sort_columns
    )
    transactions = query_service.get_transactions(
        user_id,
            query=GetTransactionsQuery(
            connection_ids=(set(connection_ids) if connection_ids else set()),
            account_ids=set(account_ids) if account_ids else set(),
            reporting_currency=reporting_currency,
            options=QueryOptions(
                filter=filter_,
                sorts=sorts,
                limit=limit,
                offset=offset,
            ),
        ),
    )
    transaction_total = TransactionTotalView.from_views(
        transactions, reporting_currency
    )

    display_table(
        TransactionView,
        transactions,
        settings.display.cli,
        columns=active_columns,
        total_view=transaction_total,
    )


@transaction_app.command(name="add")
def add_transaction(
    ctx: typer.Context,
    account_id: Annotated[str | None, typer.Option()] = None,
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
    context: CliContext = ctx.obj
    environment = context.environment
    settings = context.settings
    user_id = context.user_id
    command_service = context.container.transaction_command_service

    reporting_curreny = settings.application.reporting_currency
    zero_money = MoneyView(amount=Decimal("0"), currency=reporting_curreny)

    inputs: list[Input[Any, Any]] = [
        required_str_input("--account-id", account_id),
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
            account_id=values["--account-id"],
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

    transaction_id = command_service.create_transaction(
        user_id, command
    )
    console.print(f"Transaction '{transaction_id}' successfully added.")


@transaction_app.command(name="edit")
def edit_transaction(
    ctx: typer.Context,
    transaction_id: Annotated[str | None, typer.Option()] = None,
    account_id: Annotated[str | None, typer.Option()] = None,
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
    context: CliContext = ctx.obj
    environment = context.environment
    user_id = context.user_id
    command_service = context.container.transaction_command_service
    query_service = context.container.transaction_query_service

    resolved_transaction_id = resolve_input(
        "--transaction-id", transaction_id, environment
    )
    transaction = query_service.get_transaction(user_id, resolved_transaction_id)

    inputs: list[Input[Any, Any]] = [
        optional_prompt_str_input(
            "--account-id",
            account_id,
            default_value=transaction.account_id,
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

    command_service.update_transaction(
        user_id,
        command=UpdateTransactionCommand(
            transaction_id=resolved_transaction_id,
            payload=TransactionPayloadDto(
                account_id=values["--account-id"],
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
        ),
    )
    console.print(f"Transaction '{resolved_transaction_id}' successfully updated.")


@transaction_app.command(name="remove")
def remove_transaction(
    ctx: typer.Context,
    transaction_id: Annotated[str | None, typer.Option()] = None,
) -> None:
    context: CliContext = ctx.obj
    environment = context.environment
    user_id = context.user_id
    command_service = context.container.transaction_command_service
    query_service = context.container.transaction_query_service

    resolved_transaction_id = resolve_input(
        "--transaction-id", transaction_id, environment
    )
    transaction = query_service.get_transaction(
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

    command_service.delete_transaction(user_id, transaction.id)
    console.print(f"Transaction ({transaction.id}) successfully removed.")
