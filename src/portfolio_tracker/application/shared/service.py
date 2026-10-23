from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator, Iterable, TypeVar

from filterutils import Filter

from portfolio_tracker.application.persistence import (
    ReadUnitOfWork,
    StorageConnectionFactory,
    StorageReadConnectionFactory,
    UnitOfWork,
)
from portfolio_tracker.application.views import ViewBuilder

from .filter_mapper import FilterMapper
from .sort import Sort

TView = TypeVar("TView")


@dataclass(frozen=True, kw_only=True)
class QueryOptions:
    filter: Filter | None = None
    sorts: tuple[Sort] | None = None
    offset: int | None = None
    limit: int | None = None


class CommandService:
    def __init__(self, storage_connection_factory: StorageConnectionFactory) -> None:
        self._storage_connection_factory = storage_connection_factory

    @contextmanager
    def _unit_of_work(
        self, user_id: str | None = None
    ) -> Generator[UnitOfWork, None, None]:
        with (
            self._storage_connection_factory.create() as connection,
            connection.unit_of_work(user_id) as uow,
        ):
            yield uow


class QueryService:
    def __init__(
        self,
        storage_connection_factory: StorageReadConnectionFactory,
        filter_mapper: FilterMapper,
        view_builder: ViewBuilder,
    ) -> None:
        self._storage_connection_factory = storage_connection_factory
        self._filter_mapper = filter_mapper
        self._view_builder = view_builder

    @contextmanager
    def _unit_of_work(
        self, user_id: str | None = None
    ) -> Generator[ReadUnitOfWork, None, None]:
        with (
            self._storage_connection_factory.create() as connection,
            connection.unit_of_work(user_id) as uow,
        ):
            yield uow

    def _apply_query_options(self, views: Iterable[TView], options: QueryOptions) -> list[TView]:
        if options.filter:
            views = options.filter.apply(views)

        if options.sorts:
            views = Sort.apply_many(views, options.sorts)

        start = options.offset or 0
        end = (start + options.limit) if options.limit is not None else None
        return list(views)[start:end]
