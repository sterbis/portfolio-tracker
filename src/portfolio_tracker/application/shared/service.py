from contextlib import contextmanager
from typing import Generator

from filterutils import Filter, FilterNode, FilterTree, LogicalOperator

from portfolio_tracker.application.persistence import SessionFactory, UnitOfWork, UserScopedUnitOfWork


class ApplicationService:
    def __init__(self, session_factory: SessionFactory):
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


class InvalidFilterError(ValueError):
    """Raised when a filter cannot be safely executed across DB and In-Memory layers."""


class FilterSplitter:
    def split(self, filter_: Filter) -> tuple[Filter | None, Filter | None]:
        if isinstance(filter_, FilterNode):
            if self._is_repository_filter(filter_):
                return filter_, None

            return None, filter_

        if isinstance(filter_, FilterTree):
            logical_operator = filter_.logical_operator
            parentheses = filter_.parentheses
            
            repository_filters, memory_filters = [], []
            for child_filter in filter_.children:
                repository_filter, memory_filter = self.split(child_filter)

                if repository_filter:
                    repository_filters.append(repository_filter)
    
                if memory_filter:
                    memory_filters.append(memory_filter)

    
            if logical_operator == LogicalOperator.OR and repository_filters and memory_filters:
                raise InvalidFilterError(
                    "Cannot execute OR filter combining entity fields stored in repository and in-memory computed fields. "
                )

            repository_filter_tree = None
            if repository_filters:
                repository_filter_tree = FilterTree(logical_operator, parentheses)
                for repository_filter in repository_filters:
                    repository_filter_tree.add_child(repository_filter)

            memory_filter_tree = None
            if memory_filters:
                memory_filter_tree = FilterTree(logical_operator, parentheses)
                for memory_filter in memory_filters:
                    memory_filter_tree.add_child(memory_filter)
            
            return repository_filter_tree, memory_filter_tree

        return None, None

    def _is_repository_filter(self, filter_: FilterNode) -> bool:
        if not filter_.item_type:
            return False

        return filter_.item_type in ()
