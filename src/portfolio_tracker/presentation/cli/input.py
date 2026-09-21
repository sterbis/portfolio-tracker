from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Generic, Literal, TypeVar, overload

import typer
from filterutils import Filter, FilterError, FilterExpressionParser, FilterTree

from portfolio_tracker.application.institution import InstitutionQueryService
from portfolio_tracker.application.shared.errors import (
    InvalidCredentialParametersError,
)
from portfolio_tracker.application.views import (
    MoneyView,
    PositionRowView,
    TransactionView,
)
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.infrastructure.institution import InstitutionCode
from portfolio_tracker.presentation.cli.environment import CliEnvironment

from .parsers import (
    date_parser,
    datetime_parser,
    enum_parser,
    money_parser,
    parse_key_value_pairs,
    parse_money,
    parse_multi_value,
)

TInputValue = TypeVar("TInputValue")
TParsedValue = TypeVar("TParsedValue")
TModel = TypeVar("TModel", bound=type)


def _prompt(parameter: str) -> str:
    return parameter.replace("_", " ").replace("-", " ").capitalize()


def _enum_prompt(parameter: str, enum_cls: type[StrEnum]) -> str:
    return f"{_prompt(parameter)} ({'|'.join(enum_cls)})"


@dataclass(frozen=True)
class Input(ABC, Generic[TInputValue, TParsedValue]):
    parameter: str
    value: TInputValue | None
    prompt: str | None = None
    value_parser: Callable[[str], TParsedValue] | None = None
    default_value: TParsedValue | None = None

    @abstractmethod
    def resolve(self, environment: CliEnvironment) -> TParsedValue | str | None: ...


@dataclass(frozen=True)
class RequiredInput(Input[str, TParsedValue]):
    def resolve(self, environment: CliEnvironment) -> TParsedValue | str:
        return resolve_input(
            self.parameter,
            self.value,
            environment,
            prompt=self.prompt,
            default_value=self.default_value,
            value_parser=self.value_parser,
        )


@dataclass(frozen=True)
class OptionalInput(Input[str, TParsedValue]):
    def resolve(self, environment: CliEnvironment) -> TParsedValue | str | None:
        return resolve_optional_input(
            self.parameter,
            self.value,
            default_value=self.default_value,
            value_parser=self.value_parser,
        )


@dataclass(frozen=True)
class OptionalPromptInput(Input[str, TParsedValue]):
    def resolve(self, environment: CliEnvironment) -> TParsedValue | str | None:
        return resolve_optional_input_with_prompt(
            self.parameter,
            self.value,
            environment,
            prompt=self.prompt,
            default_value=self.default_value,
            value_parser=self.value_parser,
        )


@dataclass(frozen=True)
class ConfirmInput(Input[bool, bool]):
    default_value: bool = False

    def resolve(self, environment: CliEnvironment) -> bool:
        return resolve_bool_input(
            self.parameter,
            self.value,
            environment,
            prompt=self.prompt,
            default_value=self.default_value,
        )


def required_str_input(
    parameter: str,
    value: str | None,
    *,
    prompt: str | None = None,
    default_value: str | None = None,
) -> RequiredInput[str]:
    return RequiredInput(
        parameter,
        value,
        prompt=prompt,
        default_value=default_value,
    )


def optional_prompt_str_input(
    parameter: str,
    value: str | None,
    *,
    prompt: str | None = None,
    default_value: str | None = None,
) -> OptionalPromptInput[str]:
    return OptionalPromptInput(
        parameter,
        value,
        prompt=prompt,
        default_value=default_value,
    )


def required_date_input(
    parameter: str,
    value: str | None,
    *,
    prompt: str | None = None,
    default_value: date | None = None,
) -> RequiredInput[date]:
    return RequiredInput(
        parameter,
        value,
        prompt=prompt,
        value_parser=date_parser,
        default_value=default_value,
    )


def optional_prompt_date_input(
    parameter: str,
    value: str | None,
    *,
    prompt: str | None = None,
    default_value: date | None = None,
) -> OptionalPromptInput[date]:
    return OptionalPromptInput(
        parameter,
        value,
        prompt=prompt,
        value_parser=date_parser,
        default_value=default_value,
    )


def required_datetime_input(
    parameter: str,
    value: str | None,
    *,
    prompt: str | None = None,
    default_value: datetime | None = None,
) -> RequiredInput[datetime]:
    return RequiredInput(
        parameter,
        value,
        prompt=prompt,
        value_parser=datetime_parser,
        default_value=default_value,
    )


def optional_prompt_datetime_input(
    parameter: str,
    value: str | None,
    *,
    prompt: str | None = None,
    default_value: datetime | None = None,
) -> OptionalPromptInput[datetime]:
    return OptionalPromptInput(
        parameter,
        value,
        prompt=prompt,
        value_parser=datetime_parser,
        default_value=default_value,
    )


def required_decimal_input(
    parameter: str,
    value: str | None,
    *,
    prompt: str | None = None,
    default_value: Decimal | None = None,
) -> RequiredInput[Decimal]:
    return RequiredInput(
        parameter,
        value,
        prompt=prompt,
        value_parser=Decimal,
        default_value=default_value,
    )


def optional_prompt_decimal_input(
    parameter: str,
    value: str | None,
    *,
    prompt: str | None = None,
    default_value: Decimal | None = None,
) -> OptionalPromptInput[Decimal]:
    return OptionalPromptInput(
        parameter,
        value,
        prompt=prompt,
        value_parser=Decimal,
        default_value=default_value,
    )


def required_enum_input(
    parameter: str,
    value: str | None,
    enum_cls: type[StrEnum],
    *,
    prompt: str | None = None,
    default_value: StrEnum | None = None,
) -> RequiredInput[StrEnum]:
    return RequiredInput(
        parameter,
        value,
        prompt=prompt or _enum_prompt(parameter, enum_cls),
        value_parser=enum_parser(enum_cls),
        default_value=default_value,
    )


def optional_prompt_enum_input(
    parameter: str,
    value: str | None,
    enum_cls: type[StrEnum],
    *,
    prompt: str | None = None,
    default_value: StrEnum | None = None,
) -> OptionalPromptInput[StrEnum]:
    return OptionalPromptInput(
        parameter,
        value,
        prompt=prompt or _enum_prompt(parameter, enum_cls),
        value_parser=enum_parser(enum_cls),
        default_value=default_value,
    )


def required_money_input(
    parameter: str,
    value: str | None,
    *,
    currency: Currency | None = None,
    prompt: str | None = None,
    default_value: MoneyView | None = None,
) -> RequiredInput[MoneyView]:
    return RequiredInput(
        parameter,
        value,
        prompt=prompt,
        value_parser=money_parser(currency) if currency else parse_money,
        default_value=default_value,
    )


def optional_prompt_money_input(
    parameter: str,
    value: str | None,
    *,
    currency: Currency | None = None,
    prompt: str | None = None,
    default_value: MoneyView | None = None,
) -> OptionalPromptInput[MoneyView]:
    return OptionalPromptInput(
        parameter,
        value,
        prompt=prompt,
        value_parser=money_parser(currency) if currency else parse_money,
        default_value=default_value,
    )


def resolve_inputs(
    environment: CliEnvironment, inputs: list[Input[Any, Any]]
) -> dict[str, Any]:
    return {input_.parameter: input_.resolve(environment) for input_ in inputs}


@dataclass(frozen=True)
class FilterInput:
    parameter: str
    value: str | None
    model: type
    field: str
    value_parser: Callable[[str], Any] | None = None

    def resolve(self) -> Filter | None:
        return resolve_filter_expression_input(
            parameter=self.parameter,
            value=self.value,
            model=self.model,
            field=self.field,
            value_parser=self.value_parser,
        )


def transaction_filter_input(
    parameter: str,
    value: str | None,
    field: str,
    value_parser: Callable[[str], Any] | None = None,
) -> FilterInput:
    return FilterInput(parameter, value, TransactionView, field, value_parser)


def position_filter_input(
    parameter: str,
    value: str | None,
    field: str,
    value_parser: Callable[[str], Any] | None = None,
) -> FilterInput:
    return FilterInput(parameter, value, PositionRowView, field, value_parser)


def resolve_filter_inputs(inputs: list[FilterInput]) -> FilterTree:
    resolved_filter = FilterTree()
    for input_ in inputs:
        if filter_ := input_.resolve():
            resolved_filter.add_child(filter_)

    return resolved_filter


def parse_input_value(
    parameter: str,
    value: str,
    value_parser: Callable[[str], TParsedValue],
) -> TParsedValue:
    try:
        return value_parser(value)

    except ValueError as error:
        raise typer.BadParameter(f"Parameter: {parameter}. Reason: {error}") from error


@overload
def prompt_value(
    parameter: str,
    *,
    prompt: str | None = None,
    default_value: TParsedValue | str | None = None,
    value_parser: Callable[[str], TParsedValue] | None = None,
    optional: Literal[True],
    secret: bool = False,
) -> TParsedValue | str | None: ...


@overload
def prompt_value(
    parameter: str,
    *,
    prompt: str | None = None,
    default_value: TParsedValue | str | None = None,
    value_parser: Callable[[str], TParsedValue] | None = None,
    optional: Literal[False] = False,
    secret: bool = False,
) -> TParsedValue | str: ...


def prompt_value(
    parameter: str,
    *,
    prompt: str | None = None,
    default_value: TParsedValue | str | None = None,
    value_parser: Callable[[str], TParsedValue] | None = None,
    optional: bool = False,
    secret: bool = False,
) -> TParsedValue | str | None:
    def parser(value: TParsedValue | str) -> TParsedValue | str | None:
        if default_value and value == default_value:
            return value

        assert isinstance(value, str), "Value can only be str here."
        value = value.strip()
        if not value:
            if optional:
                return None

            raise typer.BadParameter("Value is empty.")

        if value_parser is None:
            return value

        return parse_input_value(parameter, value, value_parser)

    prompt = prompt or parameter.replace("_", " ").replace("-", " ").capitalize()

    if optional and default_value is None:
        prompt = f"{prompt} (optional, press Enter to skip)"
        default_value = ""

    show_default = default_value not in (None, "")

    parsed_value: TParsedValue | str | None = typer.prompt(
        prompt,
        default=default_value,
        show_default=show_default,
        hide_input=secret,
        confirmation_prompt=secret,
        value_proc=parser,
    )
    return parsed_value


@overload
def resolve_input(
    parameter: str,
    value: str | None,
    environment: CliEnvironment,
    *,
    prompt: str | None = None,
    default_value: None = None,
    value_parser: None = None,
    secret: bool = False,
) -> str: ...


@overload
def resolve_input(
    parameter: str,
    value: str | None,
    environment: CliEnvironment,
    *,
    prompt: str | None = None,
    default_value: TParsedValue,
    value_parser: None = None,
    secret: bool = False,
) -> TParsedValue | str: ...


@overload
def resolve_input(
    parameter: str,
    value: str | None,
    environment: CliEnvironment,
    *,
    prompt: str | None = None,
    default_value: None = None,
    value_parser: Callable[[str], TParsedValue],
    secret: bool = False,
) -> TParsedValue: ...


@overload
def resolve_input(
    parameter: str,
    value: str | None,
    environment: CliEnvironment,
    *,
    prompt: str | None = None,
    default_value: TParsedValue,
    value_parser: Callable[[str], TParsedValue],
    secret: bool = False,
) -> TParsedValue: ...


def resolve_input(
    parameter: str,
    value: str | None,
    environment: CliEnvironment,
    *,
    prompt: str | None = None,
    default_value: TParsedValue | None = None,
    value_parser: Callable[[str], TParsedValue] | None = None,
    secret: bool = False,
) -> TParsedValue | str:
    if value is None:
        if environment.is_interactive:
            return prompt_value(
                parameter=parameter,
                prompt=prompt,
                default_value=default_value,
                value_parser=value_parser,
                secret=secret,
            )

        if default_value is not None:
            return default_value

        raise typer.BadParameter(f"Missing value for required {parameter} parameter.")

    if value_parser is None:
        return value

    return parse_input_value(parameter, value, value_parser)


@overload
def resolve_optional_input(
    parameter: str,
    value: str | None,
    *,
    default_value: TParsedValue | None = None,
    value_parser: None = None,
) -> str | None: ...


@overload
def resolve_optional_input(
    parameter: str,
    value: str | None,
    *,
    default_value: TParsedValue | None = None,
    value_parser: Callable[[str], TParsedValue],
) -> TParsedValue | None: ...


def resolve_optional_input(
    parameter: str,
    value: str | None,
    *,
    default_value: TParsedValue | None = None,
    value_parser: Callable[[str], TParsedValue] | None = None,
) -> TParsedValue | str | None:
    if value is None:
        return default_value

    if value_parser is None:
        return value

    return parse_input_value(parameter, value, value_parser)


@overload
def resolve_optional_input_with_prompt(
    parameter: str,
    value: str | None,
    environment: CliEnvironment,
    *,
    prompt: str | None = None,
    default_value: TParsedValue | None = None,
    value_parser: None = None,
) -> str | None: ...


@overload
def resolve_optional_input_with_prompt(
    parameter: str,
    value: str | None,
    environment: CliEnvironment,
    *,
    prompt: str | None = None,
    default_value: TParsedValue | None = None,
    value_parser: Callable[[str], TParsedValue],
) -> TParsedValue | None: ...


def resolve_optional_input_with_prompt(
    parameter: str,
    value: str | None,
    environment: CliEnvironment,
    *,
    prompt: str | None = None,
    default_value: TParsedValue | None = None,
    value_parser: Callable[[str], TParsedValue] | None = None,
) -> TParsedValue | str | None:
    if value is None:
        if environment.is_interactive:
            return prompt_value(
                parameter=parameter,
                prompt=prompt,
                default_value=default_value,
                value_parser=value_parser,
                optional=True,
            )

        return default_value

    if value_parser is None:
        return value

    return parse_input_value(parameter, value, value_parser)


@overload
def resolve_multi_value_input(
    parameter: str,
    value: list[str] | None,
    prompt: str,
    environment: CliEnvironment,
    *,
    default_value: str | None = None,
    value_parser: None = None,
    separator: str = ",",
) -> list[str]: ...


@overload
def resolve_multi_value_input(
    parameter: str,
    value: list[str] | None,
    prompt: str,
    environment: CliEnvironment,
    *,
    default_value: str | None = None,
    value_parser: Callable[[str], TParsedValue],
    separator: str = ",",
) -> list[TParsedValue]: ...


def resolve_multi_value_input(
    parameter: str,
    value: list[str] | None,
    prompt: str,
    environment: CliEnvironment,
    *,
    default_value: str | None = None,
    value_parser: Callable[[str], TParsedValue] | None = None,
    separator: str = ",",
) -> list[TParsedValue] | list[str]:
    if value is None:
        if not environment.is_interactive:
            raise typer.BadParameter(
                f"Missing value for required {parameter} parameter."
            )

        value = typer.prompt(
            prompt,
            default=default_value,
            value_proc=lambda value: parse_multi_value(value, separator=separator),
        )

    if value_parser is None:
        return value

    return [parse_input_value(parameter, item, value_parser) for item in value]


@overload
def resolve_optional_multi_value_input(
    parameter: str,
    value: list[str] | None,
    *,
    value_parser: None = None,
) -> list[str] | None: ...


@overload
def resolve_optional_multi_value_input(
    parameter: str,
    value: list[str] | None,
    *,
    value_parser: Callable[[str], TParsedValue],
) -> list[TParsedValue] | None: ...


def resolve_optional_multi_value_input(
    parameter: str,
    value: list[str] | None,
    *,
    value_parser: Callable[[str], TParsedValue] | None = None,
) -> list[TParsedValue] | list[str] | None:
    if value is None or value_parser is None:
        return value

    return [parse_input_value(parameter, item, value_parser) for item in value]


def resolve_bool_input(
    parameter: str,
    value: bool | None,
    environment: CliEnvironment,
    *,
    prompt: str | None = None,
    default_value: bool = False,
) -> bool:
    if value is None:
        if environment.is_interactive:
            return typer.confirm(prompt or _prompt(parameter), default=default_value)

        return default_value

    return value


def resolve_file_input(
    parameter: str,
    value: str | None,
    environment: CliEnvironment,
    *,
    prompt: str | None = None,
    default_value: Path | None = None,
) -> Path:
    path = resolve_input(
        parameter=parameter,
        value=value,
        prompt=prompt,
        environment=environment,
        default_value=default_value,
        value_parser=Path,
    )
    path = path.expanduser().resolve()
    if not path.is_file():
        raise typer.BadParameter(f"File '{path}' not found.")

    return path


def resolve_filter_expression_input(
    parameter: str,
    value: str | None,
    model: type,
    field: str,
    *,
    value_parser: Callable[[str], Any] | None = None,
) -> Filter | None:
    if value is None:
        return None

    try:
        return FilterExpressionParser.parse(
            field=field,
            expression=value,
            item_type=model,
            value_parser=value_parser,
        )
    except FilterError as error:
        raise typer.BadParameter(f"Parameter: {parameter}. Reason: {error}") from error


def resolve_credential_parameters(
    institution_id: InstitutionCode,
    credential_list: list[str] | None,
    service: InstitutionQueryService,
    environment: CliEnvironment,
    default_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parameters = parse_key_value_pairs(credential_list) if credential_list else {}

    try:
        return service.parse_credential_parameters(
            institution_id=institution_id, parameters=parameters
        )

    except InvalidCredentialParametersError as error:
        unknown_parameters: list[str] = error.context["unknown_parameters"]
        missing_parameters: list[str] = error.context["missing_parameters"]

        if unknown_parameters:
            raise typer.BadParameter(error.message) from error

        if not missing_parameters:
            raise typer.BadParameter(error.message) from error

        if not environment.is_interactive:
            if default_parameters is not None:
                return default_parameters

            raise typer.BadParameter(error.message) from error

    credentials_cls = service.get_credentials_cls(institution_id)
    secret_parameters = credentials_cls.secret_parameter_names()

    for missing_parameter in missing_parameters:
        default_value = None
        if default_parameters:
            default_value = default_parameters[missing_parameter]
            default_value = (
                ", ".join(default_value)
                if isinstance(default_value, list)
                else str(default_value)
            )

        secret = missing_parameter in secret_parameters
        parameters[missing_parameter] = prompt_value(
            missing_parameter, default_value=default_value, secret=secret
        )

    try:
        return service.parse_credential_parameters(
            institution_id=institution_id, parameters=parameters
        )

    except InvalidCredentialParametersError as error:
        raise typer.BadParameter(error.message) from error
