import types
import typing
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Generator, TypeVar, cast

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


def unpack_type(type_: type) -> Generator[type, None, None]:
    if typing.get_origin(type_) in (typing.Union, types.UnionType):
        yield from typing.get_args(type_)

    else:
        yield type_


def resolve_field_type(cls: type, field_: str) -> Any:
    current_type = cls
    for name in field_.split("."):
        for type_ in unpack_type(current_type):
            if is_dataclass(type_):
                annotations = typing.get_type_hints(type_)
                if name not in annotations:
                    raise ValueError(
                        f"Dataclass '{type_.__name__}' has no field '{name}'."
                    )

                current_type = annotations[name]
                break

            if typing.get_origin(type_) is dict and len(typing.get_args(type_)) == 2:
                current_type = typing.get_args(type_)[1]
                break

        else:
            raise ValueError(
                f"Type '{getattr(current_type, '__name__', current_type)}' has no field '{name}'."
            )

    return current_type


def resolve_field_value(obj: Any, field: str) -> Any:
    value = obj
    for name in field.split("."):
        if value is None:
            return None

        value = value[name] if isinstance(value, Mapping) else getattr(value, name)

    return value


def unstructure(value: Any) -> Any:
    if isinstance(value, Enum):
        return unstructure(value.value)

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (list, tuple, set, frozenset)):
        return [unstructure(item) for item in value]

    if isinstance(value, Mapping):
        return {key: unstructure(item) for key, item in value.items()}

    if _is_dataclass_instance(value):
        return {
            field.name: unstructure(getattr(value, field.name))
            for field in fields(value)
        }

    if adapter := _ADAPTERS.get(type(value)):
        return adapter(value)

    raise TypeError(f"No adapter registered for object of type {type(value).__name__}.")


def structure(value: Any, cls: type[T]) -> T:
    if isinstance(value, cls):
        return value

    if is_dataclass(cls):
        return cast(T, structure_dataclass(value, cls))

    if converter := _CONVERTERS.get(cls):
        return cast(T, converter(value))

    try:
        return cls(value)  # type: ignore[call-arg]
    except TypeError as error:
        raise TypeError(
            f"No converter registered for type {cls.__name__}. "
            f"Direct construction failed: {error}."
        ) from error


def structure_dataclass(values: dict[str, Any], cls: type[TDataclass]) -> TDataclass:
    annotations = typing.get_type_hints(cls)
    return cls(
        **{
            filed_name: structure_field(value, annotations[filed_name])
            for filed_name, value in values.items()
            if filed_name in annotations
        }
    )


def structure_values_from_dataclass(
    values: dict[str, Any], cls: type[TDataclass]
) -> dict[str, Any]:
    annotations = typing.get_type_hints(cls)
    return {
        filed_name: structure_field(
            value, annotations[filed_name], dataclass_as_dict=True
        )
        for filed_name, value in values.items()
        if filed_name in annotations
    }


def structure_field(
    value: Any, field_type: Any, dataclass_as_dict: bool = False
) -> Any:
    if field_type is typing.Any:
        return value

    origin_type = typing.get_origin(field_type)

    if _is_dataclass_cls(field_type) and isinstance(value, dict):
        if dataclass_as_dict:
            return structure_values_from_dataclass(value, field_type)

        return structure_dataclass(value, field_type)

    if origin_type is dict and isinstance(value, dict):
        args = typing.get_args(field_type)
        key_type = args[0] if args else typing.Any
        item_type = args[1] if args else typing.Any
        return {
            structure_field(key, key_type, dataclass_as_dict): structure_field(
                item, item_type, dataclass_as_dict
            )
            for key, item in value.items()
        }

    if origin_type in (list, set) and isinstance(value, list):
        args = typing.get_args(field_type)
        item_type = args[0] if args else typing.Any
        return origin_type(
            structure_field(item, item_type, dataclass_as_dict) for item in value
        )

    if origin_type is tuple and isinstance(value, list):
        args = typing.get_args(field_type)
        if not args:
            return tuple(value)

        if len(args) == 2 and args[1] is Ellipsis:
            item_type = args[0]
            return tuple(
                structure_field(item, item_type, dataclass_as_dict) for item in value
            )

        if len(args) != len(value):
            raise ValueError(f"Expected tuple of length {len(args)}, got {len(value)}")

        return tuple(
            structure_field(item, item_type, dataclass_as_dict)
            for item, item_type in zip(value, args)
        )

    if origin_type in (typing.Union, types.UnionType):
        union_types = typing.get_args(field_type)

        for union_type in union_types:
            if isinstance(union_type, type) and isinstance(value, union_type):
                return value

        for union_type in union_types:
            try:
                return structure_field(value, union_type, dataclass_as_dict)
            except TypeError, ValueError:
                continue

        raise ValueError(
            f"Cannot convert value {value} to any of: "
            f"{', '.join(getattr(union_type, '__name__', str(union_type)) for union_type in union_types)}."
        )

    return structure(value, field_type)


def replace_dataclass_values(
    instance: TDataclass,
    replacement_values: dict[str, Any],
    *,
    allow_unknown_keys: bool = False,
) -> TDataclass:
    if not replacement_values:
        return instance

    replacements: dict[str, Any] = {}

    for field_name, replacement_value in replacement_values.items():
        if not hasattr(instance, field_name):
            raise ValueError(f"Unknown replacement value field name: '{field_name}'.")

        original_value = getattr(instance, field_name)

        if _is_dataclass_instance(original_value):
            replacements[field_name] = replace_dataclass_values(
                original_value, replacement_value, allow_unknown_keys=allow_unknown_keys
            )

        elif isinstance(original_value, dict) and isinstance(replacement_value, dict):
            replacements[field_name] = replace_dict_values(
                original_value, replacement_value, allow_unknown_keys=allow_unknown_keys
            )

        else:
            replacements[field_name] = replacement_value

    return replace(instance, **replacements)


def replace_dict_values(
    original: dict[str, Any],
    replacement: dict[str, Any],
    allow_unknown_keys: bool = False,
) -> dict[str, Any]:
    replaced = dict(original)

    for key, replacement_item in replacement.items():
        if key not in original:
            if not allow_unknown_keys:
                raise ValueError(f"Unknown key '{key}' in replacement dictionary.")

            replaced[key] = replacement_item
            continue

        original_item = original[key]

        if _is_dataclass_instance(original_item):
            replaced[key] = replace_dataclass_values(
                original_item, replacement_item, allow_unknown_keys=allow_unknown_keys
            )

        elif isinstance(original_item, dict) and isinstance(replacement_item, dict):
            replaced[key] = replace_dict_values(
                original_item, replacement_item, allow_unknown_keys=allow_unknown_keys
            )

        else:
            replaced[key] = replacement_item

    return replaced


def prune_replacement_values(
    replacement_values: dict[str, Any], original_values: TDataclass | dict[str, Any]
) -> dict[str, Any]:
    pruned_values: dict[str, Any] = {}

    for key, replacement_value in replacement_values.items():
        if isinstance(original_values, dict):
            if key not in original_values:
                continue

            original_value = original_values[key]

        elif _is_dataclass_instance(original_values):
            if not hasattr(original_values, key):
                continue

            original_value = getattr(original_values, key)

        else:
            raise ValueError(
                "Dataclass or dict is expected to be passed as default values."
            )

        if isinstance(replacement_value, dict) and (
            isinstance(original_value, dict) or _is_dataclass_instance(original_value)
        ):
            nested_pruned_values = prune_replacement_values(
                replacement_value, original_value
            )
            if nested_pruned_values:
                pruned_values[key] = nested_pruned_values

        elif replacement_value != original_value:
            pruned_values[key] = replacement_value

    return pruned_values


def diff_from_defaults(value: T, default_value: T) -> dict[str, Any]:
    result = _diff(value, default_value)
    return {} if result is _UNCHANGED else result


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


def _is_dataclass_cls(value: Any) -> bool:
    return is_dataclass(value) and isinstance(value, type)
