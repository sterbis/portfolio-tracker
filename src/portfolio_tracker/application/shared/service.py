from contextlib import contextmanager
from typing import Generator, TypeVar

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

    def _apply_query_options(
        self,
        views: list[TView],
        *,
        filter_: Filter | None = None,
        sorts: list[Sort] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[TView]:
        if filter_:
            views = list(filter_.apply(views))

        if sorts:
            views = Sort.apply_many(views, sorts)

        start = offset or 0
        end = (start + limit) if limit is not None else None
        return views[start:end]
