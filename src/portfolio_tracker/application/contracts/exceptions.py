from typing import Any


class AppError(Exception):
    _message_template = "An unexpected application error occurred."

    def __init__(self, **kwargs: Any) -> None:
        self.metadata = kwargs
        super().__init__(self.message)

    @property
    def message(self) -> str:
        return self._message_template.format(**self.metadata)


class EntityNotFoundError(AppError):
    _message_template = "{entity_name} with ID {entity_id} not found."

    def __init__(self, entity_name: str, entity_id: str) -> None:
        super().__init__(entity_name=entity_name, entity_id=entity_id)
