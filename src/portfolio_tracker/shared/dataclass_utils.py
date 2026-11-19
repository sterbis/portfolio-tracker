import functools
import types
import typing
from collections.abc import Mapping, MutableMapping
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
Registry = MutableMapping[type, Callable[[Any], Any]]


_UNION_ORIGINS = (typing.Union, types.UnionType)
_UNCHANGED = object()

_ENCODERS: Registry = {
    Decimal: str,
    date: lambda value: value.isoformat(),
    datetime: lambda value: value.isoformat(),
    Path: str,
}

_DECODERS: Registry = {
    Decimal: lambda value: Decimal(str(value)),
    date: date.fromisoformat,
    datetime: datetime.fromisoformat,
}

_PARSERS: Registry = {}


def register_encoder(cls: type[T], adapter: Callable[[T], Any]) -> None:
    _ENCODERS[cls] = adapter


def register_decoder(cls: type[T], converter: Callable[[Any], T]) -> None:
    _DECODERS[cls] = converter


def register_parser(cls: type[T], parser: Callable[[str], T]) -> None:
    _PARSERS[cls] = parser


class UnsupportedAnnotationError(TypeError): ...


class InvalidFieldError(ValueError):
    def __init__(self, field_path: str | None, reason: str) -> None:
        self.field_path = field_path
        self.reason = reason
        super().__init__(f"{field_path or '<root>'}: {reason}")


_EXPECTED = {int: "an integer", float: "a number", Decimal: "a decimal number", str: "text"}

def _expected(class_: type) -> str:
    return _EXPECTED.get(class_, class_.__name__)


def _convert(registry: Registry, class_: type[T], value: Any) -> T:
    if isinstance(value, class_) and (class_ is bool or not isinstance(value, bool)):
        return value

    converter = registry.get(class_)
    if converter is None:
        raise UnsupportedAnnotationError(f"No converter registered for {class_}")
    
    return cast(T, converter(value))


def unstructure(value: Any) -> Any:
    if isinstance(value, Enum):
        return unstructure(value.value)

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (list, tuple, set, frozenset)):
        return [unstructure(item) for item in value]

    if isinstance(value, Mapping):
        return {unstructure(key): unstructure(item) for key, item in value.items()}

    if _is_dataclass_instance(value):
        return {
            field.name: unstructure(getattr(value, field.name))
            for field in fields(value)
        }

    if encoder := _ENCODERS.get(type(value)):
        try:
            return encoder(value)
        except (TypeError, ValueError) as error:
            reason = str(error)
    else:
        reason = "No adapter registered."

    raise ValueError(
        f"Cannot adapt value {value} of the type {type(value).__name__}: {reason}"
    )


def structure(value: Any, class_: type[T]) -> T:
    if isinstance(value, class_):
        return value

    converter = _DECODERS.get(class_)
    try:
        return cast(T, converter(value) if converter else class_(value))  # type: ignore[call-arg]
    except (TypeError, ValueError) as error:
        hint = (
            " (no converter registered)"
            if converter is None and isinstance(error, TypeError)
            else ""
        )
        raise ValueError(
            f"Cannot convert {value} to {class_.__name__}{hint}: {error}"
        ) from error


def structure_field_value(
    field_path: str,
    field_type: Any,
    value: Any,
    *,
    allow_unknown_fields: bool = False,
    dataclass_as_dict: bool = False,
) -> Any:
    if _is_dataclass_class(field_type) and isinstance(value, dict):
        if dataclass_as_dict:
            return structure_values_by_dataclass(
                field_type,
                value,
                parent_field_path=field_path,
                allow_unknown_fields=allow_unknown_fields,
                dataclass_as_dict=dataclass_as_dict,
            )

        return structure_dataclass(
            field_type,
            value,
            parent_field_path=field_path,
            allow_unknown_fields=allow_unknown_fields,
        )

    recurse = functools.partial(
        structure_field_value,
        allow_unknown_fields=allow_unknown_fields,
        dataclass_as_dict=dataclass_as_dict,
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
                allow_unknown_fields=allow_unknown_fields,
                dataclass_as_dict=dataclass_as_dict,
            ): structure_field_value(
                field_path=f"{field_path}.{key}",
                field_type=item_type,
                value=item,
                allow_unknown_fields=allow_unknown_fields,
                dataclass_as_dict=dataclass_as_dict,
            )
            for key, item in value.items()
        }

    if origin_type in (list, tuple, set):
        if not isinstance(value, list):
            raise InvalidFieldError(field_path, "expected a list")

        return _convert_sequence(field_path, field_type, origin_type, value, recurse)

    if origin_type in _UNION_ORIGINS:
        union_types = typing.get_args(field_type)
        for union_type in union_types:
            if isinstance(union_type, type) and isinstance(value, union_type):
                return value
    
        return _convert_union(field_path, union_types, value, recurse)

    if not isinstance(field_type, type):
        raise UnsupportedAnnotationError(
            f"{field_path}: Unsupported annotation '{field_type}'."
        )

    try:
        return structure(value, field_type)
    except ValueError as error:
        raise InvalidFieldError(field_path, str(error)) from error


def structure_dataclass(
    cls: type[TDataclass],
    values: dict[str, Any],
    *,
    parent_field_path: str | None = None,
    allow_unknown_fields: bool = False,
) -> TDataclass:
    structured_values = structure_values_by_dataclass(
        cls,
        values,
        parent_field_path=parent_field_path,
        allow_unknown_fields=allow_unknown_fields,
        dataclass_as_dict=False,
    )

    try:
        return cls(**structured_values)
    except Exception as error:
        raise InvalidFieldError(parent_field_path, str(error)) from error


def structure_values_by_dataclass(
    cls: type[DataclassInstance],
    values: dict[str, Any],
    *,
    parent_field_path: str | None = None,
    allow_unknown_fields: bool = False,
    dataclass_as_dict: bool = True,
) -> dict[str, Any]:
    field_types = _get_cached_field_types(cls)
    structured_values: dict[str, Any] = {}

    for field_name, value in values.items():
        field_path = (
            f"{parent_field_path}.{field_name}" if parent_field_path else field_name
        )
        if field_name not in field_types:
            if allow_unknown_fields:
                continue
            raise InvalidFieldError(field_path, "Unknow field.")

        field_type = field_types[field_name]
        structured_values[field_name] = structure_field_value(
            field_path,
            field_type,
            value,
            allow_unknown_fields=allow_unknown_fields,
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
            raise InvalidFieldError(field_path, "Unknown field.")

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
        raise InvalidFieldError(field_path, str(error)) from error


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
                raise InvalidFieldError(key_path, "Unknown key.")

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


def resolve_field_type(cls: type[DataclassInstance], field_path: str) -> Any:
    current_field_type: Any = cls
    current_field_path = ""
    for field_name in field_path.split("."):
        current_field_path = (
            f"{current_field_path}.{field_name}" if current_field_path else field_name
        )

        possible_types: list[Any] = []
        for type_ in _unpack_field_type(current_field_type):
            if is_dataclass(type_) and field_name in _get_cached_field_types(type_):
                field_types = _get_cached_field_types(type_)
                if field_name in field_types:
                    possible_types.append(field_types[field_name])

            elif typing.get_origin(type_) is dict and len(typing.get_args(type_)) == 2:
                possible_types.append(typing.get_args(type_)[1])

        if not possible_types:
            raise InvalidFieldError(current_field_path, "Unknow field.")

        if len(possible_types) == 1:
            current_field_type = possible_types[0]
        else:
            current_field_type = typing.Union[tuple(possible_types)]

    return current_field_type


def resolve_field_value(instance: Any, field_path: str) -> Any:
    current_field_value = instance
    current_field_path = ""

    try:
        for field_name in field_path.split("."):
            current_field_path = (
                f"{current_field_path}.{field_name}"
                if current_field_path
                else field_name
            )
            if isinstance(current_field_value, Mapping):
                current_field_value = current_field_value[field_name]
            else:
                current_field_value = getattr(current_field_value, field_name)

    except (AttributeError, KeyError) as error:
        raise InvalidFieldError(current_field_path, "Uknow field.") from error

    return current_field_value


def _is_parent_field(field_type: Any) -> bool:
    return any(
        is_dataclass(type_) or type_ is dict or typing.get_origin(type_) is dict
        for type_ in _unpack_field_type(field_type)
    )


def parse_field_value(field_path: str, field_type: Any, value: str) -> Any:
    if _is_parent_field(field_type):
        raise InvalidFieldError(field_path, "Cannot parse value of parent field.")

    return _parse(field_path, field_type, value)


def _parse(field_path: str, field_type: Any, value: str) -> Any:
    origin_type = typing.get_origin(field_type)

    if origin_type in _UNION_ORIGINS:
        return _convert_union(field_path, typing.get_args(field_type), value, _parse)

    if origin_type in (list, tuple, set):
        items = [item.strip() for item in value.split(",") if item.strip()]
        return _convert_sequence(field_path, field_type, origin_type, items, _parse)

    parser = _PARSERS.get(field_type)
    if parser is None:
        raise UnsupportedAnnotationError(
            f"{field_path}: Unsupported annotation '{field_type}'."
        )

    try:
        return parser(value)
    except ValueError as error:
        raise InvalidFieldError(field_path, str(error)) from error


def _convert_union(
    field_path: str, union_types: tuple[Any, ...], value: Any, recurse: Callable[[str, Any, Any], Any],
) -> Any:
    non_none_types = [
        union_type for union_type in union_types if union_type is not types.NoneType
    ]

    if len(non_none_types) == 1 and len(union_types) == 2:
        try:
            return recurse(field_path, types.NoneType, value)
        except InvalidFieldError:
            return recurse(field_path, non_none_types[0], value)

    reasons: list[str] = []
    ordered_union_types = sorted(
        union_types, key=lambda union_type: union_type is not types.NoneType
    )
    for union_type in ordered_union_types:
        try:
            return recurse(field_path, union_type, value)
        except InvalidFieldError as error:
            reasons.append(
                f"{getattr(union_type, "__name__", union_type)}: {error.reason}"
            )

    raise InvalidFieldError(field_path, "; ".join(reasons))


def _convert_sequence(
    field_path: str,
    field_type: Any,
    sequence_type: type[list] | type[tuple] | type[set],  # type: ignore[type-arg]
    items: list[Any],
    recurse: Callable[[str, Any, Any], Any],
) -> Any:
    item_types = typing.get_args(field_type)
    if not item_types:
        raise UnsupportedAnnotationError(
            f"{field_path}: Unsupported annotation '{field_type}'."
        )

    if sequence_type is tuple and Ellipsis not in item_types:
        if len(item_types) != len(items):
            raise InvalidFieldError(
                field_path, f"expected {len(item_types)} items, got {len(items)}"
            )

    else:
        item_types = (item_types[0],) * len(items)

    return sequence_type(
        recurse(f"{field_path}[{index}]", item_type, item)
        for index, (item_type, item) in enumerate(zip(item_types, items))
    )


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
def _get_cached_field_types(cls: type[DataclassInstance]) -> dict[str, Any]:
    annotations = typing.get_type_hints(cls)
    return {field.name: annotations[field.name] for field in fields(cls) if field.init}
