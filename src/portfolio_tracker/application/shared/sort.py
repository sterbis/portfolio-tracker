import operator
from dataclasses import dataclass
from typing import Literal, Sequence, TypeVar

TItem = TypeVar("TItem")


@dataclass(frozen=True)
class Sort:
    field: str
    item_type: type
    direction: Literal["ASC", "DESC"] = "ASC"

    def apply(self, items: Sequence[TItem]) -> list[TItem]:
        return sorted(
            items,
            key=operator.attrgetter(self.field),
            reverse=(self.direction == "DESC"),
        )

    @classmethod
    def apply_many(cls, items: Sequence[TItem], sorts: Sequence[Sort]) -> list[TItem]:
        sorted_items = list(items)
        for sort in reversed(sorts):
            sorted_items = sort.apply(sorted_items)

        return sorted_items
