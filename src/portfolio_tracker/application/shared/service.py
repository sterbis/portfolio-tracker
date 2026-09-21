from contextlib import contextmanager
from typing import Generator, TypeVar

from filterutils import Filter

from portfolio_tracker.application.persistence import (
    StorageConnectionFactory,
    UnitOfWork,
    UserScopedUnitOfWork,
)
from portfolio_tracker.application.views import ViewBuilder

from .filter import FilterMapper, FilterSplitter
from .sort import Sort

TView = TypeVar("TView")


class Service:
    def __init__(self, storage_connection_factory: StorageConnectionFactory) -> None:
        self._storage_connection_factory = storage_connection_factory

    @contextmanager
    def _unit_of_work(
        self, read_only: bool = False
    ) -> Generator[UnitOfWork, None, None]:
        with (
            self._storage_connection_factory.create(read_only=read_only) as connection,
            connection.unit_of_work() as uow,
        ):
            yield uow

    @contextmanager
    def _user_scoped_unit_of_work(
        self,
        user_id: str,
        read_only: bool = False,
    ) -> Generator[UserScopedUnitOfWork, None, None]:
        with (
            self._storage_connection_factory.create(read_only=read_only) as connection,
            connection.unit_of_work() as uow,
        ):
            accounts_map = uow.accounts.get_account_map(user_id)
            yield UserScopedUnitOfWork(uow, accounts_map)


class QueryService(Service):
    def __init__(
        self,
        storage_connection_factory: StorageConnectionFactory,
        filter_mapper: FilterMapper,
        filter_splitter: FilterSplitter,
        view_builder: ViewBuilder,
    ) -> None:
        super().__init__(storage_connection_factory)
        self._filter_mapper = filter_mapper
        self._filter_splitter = filter_splitter
        self._view_builder = view_builder

    def _resolve_filters(
        self, filter_: Filter | None
    ) -> tuple[Filter | None, Filter | None]:
        if filter_:
            filter_ = self._filter_mapper.map(filter_)
            return self._filter_splitter.split(filter_)

        return None, None

    def _apply_view_options(
        self,
        views: list[TView],
        *,
        sorts: list[Sort] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[TView]:
        if sorts:
            views = Sort.apply_many(views, sorts)

        start = offset or 0
        end = (start + limit) if limit is not None else None

        return views[start:end]
