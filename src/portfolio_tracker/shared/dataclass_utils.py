import typing
from dataclasses import fields, is_dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping, TypeVar, cast

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


T = TypeVar("T")
TDataclass = TypeVar("TDataclass", bound="DataclassInstance")


_UNCHANGED = object()


_ADAPTERS: dict[type, Callable[[Any], Any]] = {
    Decimal: str,
    date: lambda value: value.isoformat(),
    datetime: lambda value: value.isoformat(),
    Path: str,
}

_CONVERTERS: dict[type, Callable[[Any], Any]] = {
    Decimal: lambda value: Decimal(str(value)),
    date: date.fromisoformat,
    datetime: datetime.fromisoformat,
}


def register_adapter(cls: type[T], adapter: Callable[[T], Any]) -> None:
    _ADAPTERS[cls] = adapter


def register_converter(cls: type[T], converter: Callable[[Any], T]) -> None:
    _CONVERTERS[cls] = converter


def unstructure(value: Any) -> Any:
    if isinstance(value, Enum):
        return unstructure(value.value)

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if _is_dataclass_instance(value):
        return {
            field.name: unstructure(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, Mapping):
        return {key: unstructure(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set, frozenset)):
        return [unstructure(item) for item in value]

    if adapter := _ADAPTERS.get(type(value)):
        return adapter(value)

    raise TypeError(
        f"Object of type {type(value).__name__} is not serializable and no adapter is registered."
    )


def structure(cls: type[T], value: Any) -> T:
    if isinstance(value, cls):
        return value

    if issubclass(cls, Enum):
        return cast(T, cls(value))

    if is_dataclass(cls):
        values = structure_dataclass_values(cls, value)
        return cast(T, cls(**values))

    if converter := _CONVERTERS.get(cls):
        return cast(T, converter(value))

    try:
        return cls(value)  # type: ignore[call-arg]
    except TypeError as error:

        raise TypeError(
            f"No converter registered for type {cls.__name__}, and direct construction failed: {error}"
        ) from error


def structure_dataclass_values(
    cls: type[TDataclass], values: dict[str, Any]
) -> dict[str, Any]:
    hints = typing.get_type_hints(cls)
    structured_values: dict[str, Any] = {}

    for name, value in values.items():
        if name not in hints:
            continue

        field_type: type = hints[name]

        if is_dataclass(field_type) and isinstance(value, dict):
            structured_values[name] = structure_dataclass_values(field_type, value)

        elif isinstance(value, dict) and typing.get_origin(field_type) is dict:
            item_type: type = typing.get_args(field_type)[1]
            structured_values[name] = {
                key: (
                    structure_dataclass_values(item_type, item)
                    if is_dataclass(item_type)
                    else structure(item_type, item)
                )
                for key, item in value.items()
            }

        elif isinstance(value, list) and typing.get_origin(field_type) is list:
            item_type = typing.get_args(field_type)[0]
            structured_values[name] = [structure(item_type, item) for item in value]

        else:
            structured_values[name] = structure(field_type, value)

    return structured_values


def replace_dataclass_values(
    instance: TDataclass,
    replacement_values: dict[str, Any],
    *,
    allow_unknown_keys: bool = False,
) -> TDataclass:
    if not replacement_values:
        return instance

    replacements: dict[str, Any] = {}

    for field in fields(instance):
        if field.name not in replacement_values:
            continue

        original_value = getattr(instance, field.name)
        replacement_value = replacement_values[field.name]

        if _is_dataclass_instance(original_value):
            replacements[field.name] = replace_dataclass_values(
                original_value, replacement_value, allow_unknown_keys=allow_unknown_keys
            )

        elif isinstance(original_value, dict) and isinstance(replacement_value, dict):
            merged_value = dict(original_value)

            for key, replacement_item in replacement_value.items():
                if key not in original_value:
                    if not allow_unknown_keys:
                        raise ValueError(
                            f"Unknown key '{key}' in replacement value for field '{field.name}'."
                        )

                    merged_value[key] = replacement_item
                    continue

                original_item = original_value[key]
                merged_value[key] = (
                    replace_dataclass_values(
                        original_item,
                        replacement_item,
                        allow_unknown_keys=allow_unknown_keys,
                    )
                    if _is_dataclass_instance(original_item)
                    else replacement_item
                )

            replacements[field.name] = merged_value

        else:
            replacements[field.name] = replacement_value

    return replace(instance, **replacements)


def prune_override_values(
    default_values: TDataclass | dict[str, Any], override_values: dict[str, Any]
) -> dict[str, Any]:
    pruned_values: dict[str, Any] = {}

    for key, override_value in override_values.items():
        if isinstance(default_values, dict):
            if key not in default_values:
                continue

            default_value = default_values[key]

        elif _is_dataclass_instance(default_value):
            if not hasattr(default_values, key):
                continue

            default_value = getattr(default_values, key)

        else:
            raise ValueError(
                "Dataclass or dict is expected to be passed as original values."
            )

        if isinstance(override_value, dict) and (
            isinstance(default_value, dict) or _is_dataclass_instance(default_value)
        ):
            nested_pruned = prune_override_values(default_value, override_value)
            if nested_pruned:
                pruned_values[key] = nested_pruned

        elif override_value != default_value:
            pruned_values[key] = override_value

    return pruned_values


def diff_from_defaults(value: T, default_value: T) -> dict[str, Any]:
    result = _diff(value, default_value)
    return result if result is not _UNCHANGED else {}


def _diff(value: Any, default_value: Any) -> Any:
    if is_dataclass(value) and is_dataclass(default_value):
        diff = {}
        for field in fields(value):
            field_diff = _diff(
                getattr(value, field.name), getattr(default_value, field.name)
            )
            if field_diff is not _UNCHANGED:
                diff[field.name] = field_diff

        return diff if diff else _UNCHANGED

    if isinstance(value, dict) and isinstance(default_value, dict):
        diff = {}
        for name, item in value.items():
            item_diff = _diff(item, default_value.get(name, _UNCHANGED))
            if item_diff is not _UNCHANGED:
                diff[name] = item_diff

        return diff if diff else _UNCHANGED

    return value if value != default_value else _UNCHANGED


def _is_dataclass_instance(value: Any) -> bool:
    return is_dataclass(value) and not isinstance(value, type)
