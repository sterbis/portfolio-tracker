from typing import Any

from filterutils import Filter, FilterNode, FilterTree, LogicalOperator

from portfolio_tracker.application.views import DualMoneyView, FieldMap, MoneyView
from portfolio_tracker.domain.shared import DualMoney, Money

from .errors import InvalidFilterError


class FilterMapper:
    def __init__(self, view_registry: dict[type, FieldMap]) -> None:
        self._view_registry = view_registry

    def map(self, view_filter: Filter) -> Filter:
        if isinstance(view_filter, FilterNode):
            return self._map_filter_node(view_filter)

        if isinstance(view_filter, FilterTree):
            return self._map_filter_tree(view_filter)

        raise ValueError(f"Unexpected filter type: {type(view_filter)}")

    def _map_filter_node(self, view_filter: FilterNode) -> Filter:
        if view_filter.item_type is None:
            raise InvalidFilterError(
                message=f"Missing filter view reference. {view_filter}"
            )

        field_map = self._view_registry.get(view_filter.item_type)
        if not field_map or view_filter.field not in field_map:
            return view_filter

        field = field_map[view_filter.field]

        return FilterNode(
            field=field.name,
            operator=view_filter.operator,
            value=self._map_filter_value(view_filter.value),
            item_type=field.model,
        )

    def _map_filter_tree(self, view_filter: FilterTree) -> FilterTree:
        operator = view_filter.logical_operator
        mapped_filter = FilterTree(operator)
        mapped_child_filters = [
            self.map(view_child_filter) for view_child_filter in view_filter.children
        ]

        for mapped_child_filter in mapped_child_filters:
            if (
                isinstance(mapped_child_filter, FilterTree)
                and mapped_child_filter.logical_operator == operator
            ):
                for child in mapped_child_filter.children:
                    mapped_filter.add_child(child)

            else:
                mapped_filter.add_child(mapped_child_filter)

        if operator == LogicalOperator.OR:
            item_types = {child.item_type for child in mapped_filter.iter_children()}
            if len(item_types) != 1:
                return view_filter

        return mapped_filter

    def _has_item_type(self, filter_: Filter, item_type: type) -> bool:
        for filter_node in filter_.iter_children():
            if filter_node.item_type != item_type:
                return False

        return True

    def _map_filter_value(self, value: Any) -> Any:
        if isinstance(value, MoneyView):
            return Money(amount=value.amount, currency=value.currency)

        if isinstance(value, DualMoneyView):
            return DualMoney(
                native=Money(
                    amount=value.native.amount, currency=value.native.currency
                ),
                reporting=Money(
                    amount=value.reporting.amount, currency=value.reporting.currency
                ),
            )

        return value


class FilterSplitter:
    def __init__(self, persisted_model_types: tuple[type, ...]) -> None:
        self._persisted_model_types = persisted_model_types

    def split(self, filter_: Filter) -> tuple[Filter | None, Filter | None]:
        if isinstance(filter_, FilterNode):
            return self._split_filter_node(filter_)

        if isinstance(filter_, FilterTree):
            return self._split_filter_tree(filter_)

        raise ValueError(f"Unexpected filter type: {type(filter_)}")

    def _split_filter_node(
        self, filter_: FilterNode
    ) -> tuple[Filter | None, Filter | None]:
        if filter_.item_type is None or issubclass(
            filter_.item_type, self._persisted_model_types
        ):
            return filter_, None

        return None, filter_

    def _split_filter_tree(
        self, filter_: FilterTree
    ) -> tuple[Filter | None, Filter | None]:
        repository_filters: list[Filter] = []
        memory_filters: list[Filter] = []

        for child_filter in filter_.children:
            repository_filter, memory_filter = self.split(child_filter)
            if repository_filter:
                repository_filters.append(repository_filter)

            if memory_filter:
                memory_filters.append(memory_filter)

        if (
            filter_.logical_operator == LogicalOperator.OR
            and repository_filters
            and memory_filters
        ):
            raise InvalidFilterError(
                message="Cannot split OR filter tree combining persisted fields and in-memory computed fields."
            )

        final_repository_filter = None
        if len(repository_filters) == 1:
            final_repository_filter = repository_filters[0]

        elif repository_filters:
            final_repository_filter = FilterTree(filter_.logical_operator)
            for repository_filter in repository_filters:
                final_repository_filter.add_child(repository_filter)

        final_memory_filter = None
        if len(memory_filters) == 1:
            final_memory_filter = memory_filters[0]

        elif memory_filters:
            final_memory_filter = FilterTree(filter_.logical_operator)
            for memory_filter in memory_filters:
                final_memory_filter.add_child(memory_filter)

        return final_repository_filter, final_memory_filter
