from typing import Any

from filterutils import Filter, FilterNode, FilterTree, LogicalOperator

from portfolio_tracker.application.views import DualMoneyView, FieldMap, MoneyView
from portfolio_tracker.domain.shared import DualMoney, Money

from .errors import InvalidFilterError


class FilterMapper:
    def __init__(self, registry: dict[type, FieldMap]) -> None:
        self._registry = registry

    def map(self, filter_: Filter) -> Filter:
        if isinstance(filter_, FilterNode):
            return self._map_filter_node(filter_)

        if isinstance(filter_, FilterTree):
            return self._map_filter_tree(filter_)

        raise ValueError(f"Unexpected filter type: {type(filter_)}")

    def _map_filter_node(self, filter_: FilterNode) -> Filter:
        if filter_.item_type is None:
            raise InvalidFilterError(
                message=f"Missing filter model reference. {filter_}"
            )

        view_map = self._registry.get(filter_.item_type)
        if not view_map or filter_.field not in view_map:
            raise InvalidFilterError(
                message=f"Field '{filter_.field}' not found in map for view '{filter_.item_type.__name__}'."
            )

        field = view_map[filter_.field]
        value = self._map_filter_value(filter_.value)
        models = field.model if isinstance(field.model, tuple) else (field.model,)

        if len(models) == 1:
            return FilterNode(
                field=field.name,
                operator=filter_.operator,
                value=value,
                item_type=models[0],
            )

        translated_filter = FilterTree(LogicalOperator.OR)
        for model in models:
            translated_filter.add_child(
                FilterNode(
                    field=field.name,
                    operator=filter_.operator,
                    value=value,
                    item_type=model,
                )
            )

        return translated_filter

    def _map_filter_tree(self, filter_: FilterTree) -> FilterTree:
        translated_filter = FilterTree(filter_.logical_operator)

        for child_filter in filter_.children:
            translated_child_filter = self.map(child_filter)

            if (
                isinstance(translated_child_filter, FilterTree)
                and translated_child_filter.logical_operator
                == translated_filter.logical_operator
            ):
                for transalted_sub_child_filter in translated_child_filter.children:
                    translated_filter.add_child(transalted_sub_child_filter)
            else:
                translated_filter.add_child(translated_child_filter)

        return translated_filter

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
            if self.is_persisted(filter_):
                return filter_, None

            return None, filter_

        if isinstance(filter_, FilterTree):
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

        raise ValueError(f"Unexpected filter type: {type(filter_)}")

    def is_persisted(self, filter_: FilterNode) -> bool:
        if filter_.item_type is None:
            return True

        return issubclass(filter_.item_type, self._persisted_model_types)
