import functools
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


class ConversionError(ValueError): ...


class DataclassValueError(ValueError):
    def __init__(self, field_path: str | None, reason: str) -> None:
        self.field_path = field_path
        self.reason = reason
        super().__init__(f"{field_path or '<root>'}: {reason}")


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

    converter = _CONVERTERS.get(cls)
    try:
        return cast(T, converter(value) if converter else cls(value))  # type: ignore[call-arg]
    except (TypeError, ValueError) as error:
        hint = (
            " (no converter registered)"
            if converter is None and isinstance(error, TypeError)
            else ""
        )
        raise ConversionError(
            f"Cannot convert {value} to {cls.__name__}{hint}: {error}"
        ) from error


def structure_field_value(
    field_path: str,
    field_type: Any,
    value: Any,
    *,
    unknown_fields: bool = False,
    dataclass_as_dict: bool = False,
) -> Any:
    if field_type is typing.Any:
        return value

    if _is_dataclass_class(field_type) and isinstance(value, dict):
        if dataclass_as_dict:
            return structure_values_by_dataclass(
                field_type,
                value,
                parent_field_path=field_path,
                unknown_fields=unknown_fields,
                dataclass_as_dict=dataclass_as_dict,
            )

        return structure_dataclass(
            field_type,
            value,
            parent_field_path=field_path,
            unknown_fields=unknown_fields,
        )

    origin_type = typing.get_origin(field_type)

    if origin_type is dict and isinstance(value, dict):
        item_types = typing.get_args(field_type)
        key_type = item_types[0] if item_types else typing.Any
        item_type = item_types[1] if item_types else typing.Any
        return {
            structure_field_value(
                field_path=f"{field_path}.{key}",
                field_type=key_type,
                value=key,
                unknown_fields=unknown_fields,
                dataclass_as_dict=dataclass_as_dict,
            ): structure_field_value(
                field_path=f"{field_path}.{key}",
                field_type=item_type,
                value=item,
                unknown_fields=unknown_fields,
                dataclass_as_dict=dataclass_as_dict,
            )
            for key, item in value.items()
        }

    if origin_type in (list, set) and isinstance(value, list):
        item_types = typing.get_args(field_type)
        item_type = item_types[0] if item_types else typing.Any
        return origin_type(
            structure_field_value(
                f"{field_path}[{index}]",
                item_type,
                item,
                unknown_fields=unknown_fields,
                dataclass_as_dict=dataclass_as_dict,
            )
            for index, item in enumerate(value)
        )

    if origin_type is tuple and isinstance(value, list):
        item_types = typing.get_args(field_type)
        if not item_types:
            return tuple(value)

        if len(item_types) == 2 and item_types[1] is Ellipsis:
            item_type = item_types[0]
            return tuple(
                structure_field_value(
                    f"{field_path}[{index}]",
                    item_type,
                    item,
                    unknown_fields=unknown_fields,
                    dataclass_as_dict=dataclass_as_dict,
                )
                for index, item in enumerate(value)
            )

        if len(item_types) != len(value):
            raise DataclassValueError(
                field_path=field_path,
                reason=f"Expected {len(item_types)} items, got {len(value)}",
            )

        return tuple(
            structure_field_value(
                f"{field_path}[{index}]",
                item_type,
                item,
                unknown_fields=unknown_fields,
                dataclass_as_dict=dataclass_as_dict,
            )
            for index, (item, item_type) in enumerate(zip(value, item_types))
        )

    if origin_type in (typing.Union, types.UnionType):
        union_types = typing.get_args(field_type)

        for union_type in union_types:
            if isinstance(union_type, type) and isinstance(value, union_type):
                return value

        if len(union_types) == 2 and types.NoneType in union_types:
            union_type = next(
                union_type
                for union_type in union_types
                if union_type is not types.NoneType
            )
            return structure_field_value(
                field_path,
                union_type,
                value,
                unknown_fields=unknown_fields,
                dataclass_as_dict=dataclass_as_dict,
            )

        errors: list[tuple[Any, DataclassValueError]] = []
        for union_type in union_types:
            try:
                return structure_field_value(
                    field_path,
                    union_type,
                    value,
                    unknown_fields=unknown_fields,
                    dataclass_as_dict=dataclass_as_dict,
                )
            except DataclassValueError as error:
                errors.append((union_type, error))

        raise DataclassValueError(
            field_path=field_path,
            reason=", ".join(
                f"{union_type}: {error.reason}" for union_type, error in errors
            ),
        )

    if origin_type in (dict, list, set, tuple):
        raise DataclassValueError(
            field_path, f"Expected {origin_type.__name__}, got {type(value).__name__}."
        )

    if not isinstance(field_type, type):
        raise DataclassValueError(field_path, "Unsupported annotation.")

    try:
        return structure(value, field_type)
    except ConversionError as error:
        raise DataclassValueError(field_path, str(error)) from error


def structure_dataclass(
    cls: type[TDataclass],
    values: dict[str, Any],
    *,
    parent_field_path: str | None = None,
    unknown_fields: bool = False,
) -> TDataclass:
    structured_values = structure_values_by_dataclass(
        cls,
        values,
        parent_field_path=parent_field_path,
        unknown_fields=unknown_fields,
        dataclass_as_dict=False,
    )

    try:
        return cls(**structured_values)
    except Exception as error:
        raise DataclassValueError(parent_field_path, str(error)) from error


def structure_values_by_dataclass(
    cls: type[DataclassInstance],
    values: dict[str, Any],
    *,
    parent_field_path: str | None = None,
    unknown_fields: bool = False,
    dataclass_as_dict: bool = True,
) -> dict[str, Any]:
    annotations = get_cached_type_hints(cls)
    field_types = {
        field.name: annotations[field.name] for field in fields(cls) if field.init
    }
    structured_values: dict[str, Any] = {}

    for field_name, value in values.items():
        field_path = (
            f"{parent_field_path}.{field_name}" if parent_field_path else field_name
        )
        if field_name not in field_types:
            if unknown_fields:
                continue
            raise DataclassValueError(field_path, "Uknow field.")

        field_type = field_types[field_name]
        structured_values[field_name] = structure_field_value(
            field_path,
            field_type,
            value,
            unknown_fields=unknown_fields,
            dataclass_as_dict=dataclass_as_dict,
        )

    return structured_values


def replace_dataclass_values(
    instance: TDataclass,
    replacement_values: dict[str, Any],
    *,
    allow_unknown_keys: bool = False,
    parent_field_path: str | None = None,
) -> TDataclass:
    if not replacement_values:
        return instance

    replacements: dict[str, Any] = {}

    for field_name, replacement_value in replacement_values.items():
        field_path = (
            f"{parent_field_path}.{field_name}" if parent_field_path else field_name
        )

        if not hasattr(instance, field_name):
            raise DataclassValueError(field_path, "unknown field")

        original_value = getattr(instance, field_name)

        if _is_dataclass_instance(original_value):
            replacements[field_name] = replace_dataclass_values(
                original_value,
                replacement_value,
                allow_unknown_keys=allow_unknown_keys,
                parent_field_path=field_path,
            )

        elif isinstance(original_value, dict) and isinstance(replacement_value, dict):
            replacements[field_name] = replace_dict_values(
                original_value,
                replacement_value,
                allow_unknown_keys=allow_unknown_keys,
                parent_field_path=field_path,
            )

        else:
            replacements[field_name] = replacement_value

    try:
        return replace(instance, **replacements)
    except Exception as error:
        raise DataclassValueError(field_path, str(error)) from error


def replace_dict_values(
    original: dict[str, Any],
    replacement: dict[str, Any],
    *,
    allow_unknown_keys: bool = False,
    parent_field_path: str | None = None,
) -> dict[str, Any]:
    replaced = dict(original)

    for key, replacement_item in replacement.items():
        key_path = f"{parent_field_path}.{key}" if parent_field_path else key

        if key not in original:
            if not allow_unknown_keys:
                raise DataclassValueError(key_path, "unknown key")

            replaced[key] = replacement_item
            continue

        original_item = original[key]

        if _is_dataclass_instance(original_item):
            replaced[key] = replace_dataclass_values(
                original_item,
                replacement_item,
                allow_unknown_keys=allow_unknown_keys,
                parent_field_path=key_path,
            )

        elif isinstance(original_item, dict) and isinstance(replacement_item, dict):
            replaced[key] = replace_dict_values(
                original_item,
                replacement_item,
                allow_unknown_keys=allow_unknown_keys,
                parent_field_path=key_path,
            )

        else:
            replaced[key] = replacement_item

    return replaced


def prune_replacement_values(
    replacement_values: dict[str, Any],
    original_values: DataclassInstance | dict[str, Any],
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


def resolve_field_type(cls: type[DataclassInstance], field_path: str) -> type:
    field_type = cls
    for field_name in field_path.split("."):
        for unpacked_field_type in _unpack_field_type(field_type):
            if is_dataclass(unpacked_field_type):
                annotations = get_cached_type_hints(unpacked_field_type)
                if field_name not in annotations:
                    raise ValueError(
                        f"Dataclass '{unpacked_field_type.__name__}' has no field '{field_name}'."
                    )

                field_type = annotations[field_name]
                break

            if (
                typing.get_origin(unpacked_field_type) is dict
                and len(typing.get_args(unpacked_field_type)) == 2
            ):
                field_type = typing.get_args(unpacked_field_type)[1]
                break

        else:
            raise ValueError(
                f"Type '{getattr(field_type, '__name__', field_type)}' has no field '{field_name}'."
            )

    return field_type


def resolve_field_value(instance: DataclassInstance, field_path: str) -> Any:
    field_value = instance
    for field_name in field_path.split("."):
        if isinstance(field_value, Mapping):
            field_value = field_value[field_name]
        else:
            field_value = getattr(field_value, field_name)

    return field_value


def _unpack_field_type(field_type: type) -> Generator[type, None, None]:
    if typing.get_origin(field_type) in (typing.Union, types.UnionType):
        yield from typing.get_args(field_type)

    else:
        yield field_type


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


def _is_dataclass_class(value: Any) -> bool:
    return is_dataclass(value) and isinstance(value, type)


@functools.cache
def get_cached_type_hints(cls: type[DataclassInstance]) -> dict[str, Any]:
    return typing.get_type_hints(cls)
