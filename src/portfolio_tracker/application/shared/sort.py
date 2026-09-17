from dataclasses import dataclass
from typing import Any, Sequence, TypeVar

from portfolio_tracker.shared.dataclass_utils import resolve_field_value

TItem = TypeVar("TItem")


@dataclass(frozen=True)
class Sort:
    field: str
    item_type: type
    reverse: bool = False

    def _sort_key(self, item: TItem) -> tuple[bool, Any]:
        value = resolve_field_value(item, self.field)
        return value is not None if self.reverse else value is None, value

    def apply(self, items: Sequence[TItem]) -> list[TItem]:
        return sorted(
            items,
            key=self._sort_key,
            reverse=self.reverse,
        )

    @classmethod
    def apply_many(cls, items: Sequence[TItem], sorts: Sequence[Sort]) -> list[TItem]:
        sorted_items = list(items)
        for sort in reversed(sorts):
            sorted_items = sort.apply(sorted_items)

        return sorted_items
