import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from portfolio_tracker.shared.dataclass_utils import (
    prune_override_values,
    replace_dataclass_values,
    structure_dataclass_values,
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
    def __init__(self, settings_cls: type[TSettings], settings_dir: Path) -> None:
        super().__init__(settings_cls)
        self._settings_dir = settings_dir

    def load(self, user_id: str) -> dict[str, Any]:
        path = self._path(user_id)
        if not path.exists():
            return {}

        overrides = json.loads(path.read_text())
        return structure_dataclass_values(self._settings_cls, overrides)

    def save(self, user_id: str, overrides: dict[str, Any]) -> None:
        self._path(user_id).write_text(
            json.dumps(unstructure(overrides), indent=2)
        )

    def _path(self, user_id: str) -> Path:
        path = self._settings_dir / user_id / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


class SettingsCache(Generic[TSettings]):
    def __init__(
        self, default_settings: TSettings, store: SettingsStore
    ) -> None:
        self._default_settings = default_settings
        self._store = store
        self._cache: dict[str, TSettings] = {}

    def get_settings(self, user_id: str | None = None) -> TSettings:
        if user_id is None:
            return self._default_settings

        if user_id not in self._cache:
            overrides = self._store.load(user_id)
            self._cache[user_id] = replace_dataclass_values(
                self._default_settings, overrides
            )

        return self._cache[user_id]

    def update_settings(self, user_id: str, changes: dict[str, Any]) -> TSettings:
        current_overrides = self._store.load(user_id)
        updated_overrides = _merge_dicts(current_overrides, changes)
        pruned_overrides = prune_override_values(
            self._default_settings, updated_overrides
        )
        self._store.save(user_id, pruned_overrides)
        self._cache[user_id] = replace_dataclass_values(
            self._default_settings, pruned_overrides
        )
        return self._cache[user_id]


def _merge_dicts(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)

    for key, value in updates.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value

    return merged
