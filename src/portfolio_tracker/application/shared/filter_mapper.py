from dataclasses import dataclass
from typing import Any

from filterutils import Filter, FilterNode, FilterTree, LogicalOperator

from portfolio_tracker.application.views import DualMoneyView, FieldMap, MoneyView
from portfolio_tracker.domain.shared import DualMoney, Money

from .errors import InvalidFilterError


@dataclass(frozen=True)
class FilterSplit:
    repository: Filter | None
    memory: Filter | None


class FilterMapper:
    def __init__(
        self,
        view_registry: dict[type, FieldMap],
        persisted_domain_types: tuple[type, ...],
    ) -> None:
        self._view_registry = view_registry
        self._persisted_domain_types = set(persisted_domain_types)

    def map(self, view_filter: Filter | None) -> dict[type, Filter]:
        if view_filter is None:
            return {}

        domain_types = self._extract_domain_types(view_filter)
        domain_filters: dict[type, Filter] = {}
        for domain_type in domain_types:
            domain_filter = self._map_to_domain_filter(view_filter, {domain_type})
            if domain_filter is not None:
                domain_filters[domain_type] = domain_filter.normalized()

        return domain_filters

    def split(self, view_filter: Filter | None) -> FilterSplit:
        if view_filter is None:
            return FilterSplit(None, None)

        domain_filters = self.map(view_filter)
        return FilterSplit(
            repository=FilterTree.and_combine(
                *(
                    filter_
                    for type_, filter_ in domain_filters.items()
                    if type_ in self._persisted_domain_types
                )
            ),
            memory=FilterTree.and_combine(
                *(
                    filter_
                    for type_, filter_ in domain_filters.items()
                    if type_ not in self._persisted_domain_types
                )
            ),
        )

    def _extract_domain_types(self, view_filter: Filter) -> set[type]:
        domain_types: set[type] = set()
        for filter_node in view_filter.iter_nodes():
            if field_map := self._view_registry.get(
                self._ensure_view_type(filter_node)
            ):
                if field := field_map.get(filter_node.field):
                    domain_types.add(field.domain_type)

        return domain_types

    def _ensure_view_type(self, view_filter: FilterNode) -> type:
        if view_filter.item_type is None:
            raise InvalidFilterError(
                message=f"Missing filter view type reference. {view_filter}"
            )

        return view_filter.item_type

    def _map_to_domain_filter(
        self, view_filter: Filter, domain_types: set[type]
    ) -> Filter | None:
        if isinstance(view_filter, FilterNode):
            return self._map_filter_node(view_filter, domain_types)

        assert isinstance(view_filter, FilterTree)

        domain_filters = [
            self._map_to_domain_filter(filter_, domain_types)
            for filter_ in view_filter.children
        ]

        if view_filter.logical_operator is LogicalOperator.OR:
            if any(filter_ is None for filter_ in domain_filters):
                return None

            return FilterTree.or_combine(*domain_filters)

        return FilterTree.and_combine(*domain_filters)

    def _map_filter_node(
        self,
        view_filter: FilterNode,
        domain_types: set[type],
    ) -> FilterNode | None:
        field_map = self._view_registry.get(self._ensure_view_type(view_filter))
        if field_map is None:
            return None

        field = field_map.get(view_filter.field)
        if not field or field.domain_type not in domain_types:
            return None

        return FilterNode(
            field=field.name,
            operator=view_filter.operator,
            value=self._map_filter_value(view_filter.value),
            item_type=field.domain_type,
        )

    def _map_filter_value(self, value: Any) -> Any:
        match value:
            case MoneyView():
                return self._to_money(value)

            case DualMoneyView():
                return DualMoney(
                    native=self._to_money(value.native),
                    reporting=self._to_money(value.reporting),
                )
            case list() | tuple() | set() as values:
                return type(value)(self._map_filter_value(value) for value in values)

            case _:
                return value

    def _to_money(self, value: MoneyView) -> Money:
        return Money(amount=value.amount, currency=value.currency)
