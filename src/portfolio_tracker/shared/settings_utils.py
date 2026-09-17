import copy
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from portfolio_tracker.shared.dataclass_utils import (
    prune_replacement_values,
    replace_dataclass_values,
    structure,
    unstructure,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


TSettings = TypeVar("TSettings", bound="DataclassInstance")


class SettingsStore(ABC):
    def __init__(self, settings_cls: type[DataclassInstance]) -> None:
        self._settings_cls = settings_cls

    @abstractmethod
    def load(self, user_id: str) -> dict[str, Any]: ...

    @abstractmethod
    def save(self, user_id: str, overrides: dict[str, Any]) -> None: ...


class JsonSettingsStore(SettingsStore):
    def __init__(self, settings_cls: type[DataclassInstance], settings_dir: Path) -> None:
        super().__init__(settings_cls)
        self._settings_dir = settings_dir

    def load(self, user_id: str | None = None) -> dict[str, Any]:
        path = self._path(user_id)
        if not path.exists():
            return {}

        overrides = json.loads(path.read_text())
        return structure(overrides, cast(type, self._settings_cls))

    def save(self, user_id: str, overrides: dict[str, Any]) -> None:
        self._path(user_id).write_text(json.dumps(unstructure(overrides), indent=2))

    def _path(self, user_id: str | None = None) -> Path:
        if user_id is not None:
            path = self._settings_dir / user_id
        else:
            path = self._settings_dir

        path = path / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


class SettingsCache(Generic[TSettings]):
    def __init__(self, default_settings: TSettings, store: SettingsStore) -> None:
        self._default_settings = default_settings
        self._store = store
        self._cache: dict[str, TSettings] = {}

    @property
    def default_settings(self) -> TSettings:
        return self._default_settings

    def set_value(self, user_id: str, key: str, value: Any) -> TSettings:
        overrides: dict[str, Any] = {}
        section = overrides
        *section_keys, value_key = key.split(".")
        for section_key in section_keys:
            section = section.setdefault(section_key, {})

        section[value_key] = value
        return self._update_settings(user_id, overrides)

    def reset_value(self, user_id: str, key: str) -> tuple[TSettings, bool]:
        overrides = copy.deepcopy(self.get_overrides(user_id))
        section_overrides = overrides
        *section_keys, value_key = key.split(".")
        for section_key in section_keys:
            child_section_overrides = section_overrides.get(section_key)
            if not isinstance(child_section_overrides, dict):
                return self.get_settings(user_id), False

            section_overrides = child_section_overrides

        if value_key not in section_overrides:
            return self.get_settings(user_id), False

        del section_overrides[value_key]
        return self._save_overrides(user_id, overrides), True

    def reset_all(self, user_id: str) -> TSettings:
        return self._save_overrides(user_id, {})

    def get_overrides(self, user_id: str) -> dict[str, Any]:
        return self._store.load(user_id)

    def get_settings(self, user_id: str | None = None) -> TSettings:
        if user_id is None:
            return self.default_settings

        if user_id not in self._cache:
            overrides = self.get_overrides(user_id)
            self._cache[user_id] = replace_dataclass_values(
                self._default_settings, overrides
            )

        return self._cache[user_id]

    def _update_settings(self, user_id: str, overrides: dict[str, Any]) -> TSettings:
        current_overrides = self.get_overrides(user_id)
        merged_overrides = merge_dicts(current_overrides, overrides)
        return self._save_overrides(user_id, merged_overrides)

    def _save_overrides(self, user_id: str, overrides: dict[str, Any]) -> TSettings:
        overrides = prune_replacement_values(overrides, self._default_settings)
        self._store.save(user_id, overrides)
        self._cache[user_id] = replace_dataclass_values(
            self._default_settings, overrides
        )
        return self._cache[user_id]


def merge_dicts(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)

    for key, value in updates.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value

    return merged
