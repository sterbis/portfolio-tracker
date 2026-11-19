import copy
import json
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from portfolio_tracker.shared.dataclass_utils import (
    InvalidFieldError,
    prune_replacement_values,
    replace_dataclass_values,
    replace_dict_values,
    structure_values_by_dataclass,
    unstructure,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


TSettings = TypeVar("TSettings", bound="DataclassInstance")


class SettingsError(Exception): ...


class SettingsLoadError(SettingsError): ...


class SettingsSaveError(SettingsError): ...


class SettingsValidationError(SettingsError): ...


class SettingsStore(ABC):
    def __init__(self, settings_class: type[DataclassInstance]) -> None:
        self._settings_class = settings_class

    @abstractmethod
    def load(self, user_id: str) -> dict[str, Any]: ...

    @abstractmethod
    def save(self, user_id: str, overrides: dict[str, Any]) -> None: ...


class JsonSettingsStore(SettingsStore):
    def __init__(
        self, settings_class: type[DataclassInstance], settings_dir: Path
    ) -> None:
        super().__init__(settings_class)
        self._settings_dir = settings_dir

    def load(self, user_id: str) -> dict[str, Any]:
        path = self._path(user_id)
        if not path.exists():
            return {}

        try:
            overrides = json.loads(path.read_text(encoding="utf-8"))
            return structure_values_by_dataclass(self._settings_class, overrides)

        except (OSError, json.JSONDecodeError, InvalidFieldError) as error:
            raise SettingsLoadError(
                f"Cannot load settings from {path}: {error}"
            ) from error

    def save(self, user_id: str, overrides: dict[str, Any]) -> None:
        data = json.dumps(unstructure(overrides), indent=2)

        path = self._path(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        fd, name = tempfile.mkstemp(dir=path.parent, prefix="settings-", suffix=".tmp")
        temp_path = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                file.write(data)
                file.flush()
                os.fsync(file.fileno())

            temp_path.replace(path)

        except OSError as error:
            raise SettingsSaveError(
                f"Cannot save settings to {path}: {error}"
            ) from error

        finally:
            temp_path.unlink(missing_ok=True)

    def _path(self, user_id: str) -> Path:
        return self._settings_dir / user_id / "settings.json"


class SettingsCache(Generic[TSettings]):
    def __init__(self, default_settings: TSettings, store: SettingsStore) -> None:
        self._default_settings = default_settings
        self._store = store
        self._cache: dict[str, TSettings] = {}

    @property
    def default_settings(self) -> TSettings:
        return self._default_settings

    def get_overrides(self, user_id: str) -> dict[str, Any]:
        return self._store.load(user_id)

    def get(self, user_id: str) -> TSettings:
        if user_id not in self._cache:
            overrides = self.get_overrides(user_id)
            self._cache[user_id] = self._replace(overrides)

        return self._cache[user_id]

    def set_value(self, user_id: str, key: str, value: Any) -> TSettings:
        overrides: dict[str, Any] = {}
        section = overrides
        *section_keys, value_key = key.split(".")
        for section_key in section_keys:
            section = section.setdefault(section_key, {})

        section[value_key] = value
        return self._update(user_id, overrides)

    def reset_value(self, user_id: str, key: str) -> bool:
        overrides = copy.deepcopy(self.get_overrides(user_id))
        section_overrides = overrides
        *section_keys, value_key = key.split(".")
        for section_key in section_keys:
            child_section_overrides = section_overrides.get(section_key)
            if not isinstance(child_section_overrides, dict):
                return False

            section_overrides = child_section_overrides

        if value_key not in section_overrides:
            return False

        del section_overrides[value_key]
        self._save(user_id, overrides)
        return True

    def reset_all(self, user_id: str) -> TSettings:
        return self._save(user_id, {})

    def _update(self, user_id: str, overrides: dict[str, Any]) -> TSettings:
        current_overrides = self.get_overrides(user_id)
        merged_overrides = replace_dict_values(current_overrides, overrides)
        return self._save(user_id, merged_overrides)

    def _save(self, user_id: str, overrides: dict[str, Any]) -> TSettings:
        overrides = prune_replacement_values(overrides, self._default_settings)
        self._cache[user_id] = self._replace(overrides)
        self._store.save(user_id, overrides)
        return self._cache[user_id]

    def _replace(self, overrides: dict[str, Any]) -> TSettings:
        try:
            return replace_dataclass_values(self._default_settings, overrides)
        except InvalidFieldError as error:
            raise SettingsValidationError(f"Invalid settings {error}") from error
