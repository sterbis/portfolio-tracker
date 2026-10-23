import logging

from PySide6.QtCore import QObject, Signal

from portfolio_tracker.application.shared.errors import PortfolioTrackerError
from portfolio_tracker.application.portfolio import (
    PortfolioSnapshot,
    GetPositionsQuery,
)
from portfolio_tracker.domain.instrument import InstrumentMetadata
from portfolio_tracker.domain.market_data import MarketData
from portfolio_tracker.presentation.desktop.gui.context import GuiContext
from portfolio_tracker.presentation.desktop.gui.tasks import EmitProgress

logger = logging.getLogger(__name__)


class PositionsPresenter(QObject):
    loading_changed = Signal(bool)
    positions_changed = Signal(object)
    instruments_changed = Signal(object)
    failed = Signal(str)

    def __init__(
        self, context: GuiContext, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._context = context
        self._query: GetPositionsQuery | None = None
        self._snapshot: PortfolioSnapshot | None = None
        self._market_data: MarketData | None = None
        self._instruments: frozenset[InstrumentMetadata] = frozenset()
        self._is_busy = False
        self._pending_request: tuple[GetPositionsQuery, bool] | None = None

    @property
    def instruments(self) -> frozenset[InstrumentMetadata]:
        return self._instruments

    def refresh(self, query: GetPositionsQuery, *, force: bool = False) -> None:
        if self._is_busy:
            was_forced = self._pending_request[1] if self._pending_request else False
            self._pending_request = (query, force or was_forced)
            return

        if force or self._snapshot is None or self._snapshot.query != query.build:
            self._start_build(query)

        elif query != self._query:
            self._query = query
            self._process()

    def refresh_market_data(self, market_data: MarketData) -> None:
        if self._is_busy or self._snapshot is None or self._snapshot.query.as_of is not None:
            return

        merged_market_data = (
            market_data
            if self._market_data is None
            else self._market_data.merge(market_data)
        )
        if merged_market_data == self._market_data:
            return

        self._market_data = merged_market_data
        self._process()

    def _process(self) -> None:
        if self._snapshot is None or self._query is None:
            raise RuntimeError(
                "Portfolio snapshot, query, or both are None. "
                f"Snapshot: {self._snapshot}. Query: {self._query}."
            )

        result = (
            self._context.container.portfolio_query_service.positions_from_snapshot(
                self._snapshot, self._query.view, self._market_data
            )
        )
        self.positions_changed.emit(result)

    def _start_build(self, query: GetPositionsQuery) -> None:
        user_id = self._context.user_id
        service = self._context.container.portfolio_query_service
        runner = self._context.task_runner

        def task(_: EmitProgress) -> tuple[PortfolioSnapshot, MarketData | None]:
            snapshot = service.build_snapshot(user_id, query.build)
            return snapshot, service.fetch_market_data(snapshot.instruments)

        self._is_busy = True
        self.loading_changed.emit(True)
        runner.start(
            task,
            on_result=lambda result: self._on_build_result(query, result),
            on_error=self._on_build_error,
        )

    def _on_build_result(
        self, query: GetPositionsQuery, result: tuple[PortfolioSnapshot, MarketData | None]
    ) -> None:
        self._query = query
        self._snapshot, market_data = result
        if market_data:
            self._market_data = market_data

        instruments = frozenset(
            instrument.metadata for instrument in self._snapshot.instruments
        )
        if instruments != self._instruments:
            self._instruments = instruments
            self.instruments_changed.emit(instruments)

        self._process()
        self._is_busy = False
        self.loading_changed.emit(False)
        self._run_pending_request()

    def _on_build_error(self, error: PortfolioTrackerError) -> None:
        logger.warning("Positions build failed: %s", error)
        self._is_busy = False
        self.loading_changed.emit(False)
        self.failed.emit(str(error))
        self._run_pending_request()

    def _run_pending_request(self) -> None:
        if self._pending_request is not None:
            query, force = self._pending_request
            self._pending_request = None
            self.refresh(query, force=force)
