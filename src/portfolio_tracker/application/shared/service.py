from contextlib import contextmanager
from typing import Generator

from portfolio_tracker.application.persistence import (
    SessionFactory,
    UnitOfWork,
    UserScopedUnitOfWork,
)
from portfolio_tracker.application.views import ViewBuilder

from .filter import FilterMapper, FilterSplitter


class ApplicationService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _unit_of_work(
        self, read_only: bool = False
    ) -> Generator[UnitOfWork, None, None]:
        with (
            self._session_factory.create(read_only=read_only) as session,
            session.unit_of_work() as uow,
        ):
            yield uow

    @contextmanager
    def _user_unit_of_work(
        self,
        user_id: str,
        read_only: bool = False,
    ) -> Generator[UserScopedUnitOfWork, None, None]:
        with (
            self._session_factory.create(read_only=read_only) as session,
            session.unit_of_work() as uow,
        ):
            accounts_map = uow.accounts.get_user_accounts_map(user_id)
            yield UserScopedUnitOfWork(uow, accounts_map)


class ApplicationQueryService(ApplicationService):
    def __init__(
        self,
        session_factory: SessionFactory,
        filter_mapper: FilterMapper,
        filter_splitter: FilterSplitter,
        view_builder: ViewBuilder,
    ) -> None:
        super().__init__(session_factory)
        self._filter_mapper = filter_mapper
        self._filter_splitter = filter_splitter
        self._view_builder = view_builder
