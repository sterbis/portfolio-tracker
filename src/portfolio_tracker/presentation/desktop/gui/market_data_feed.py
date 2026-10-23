from typing import Iterable

from PySide6.QtCore import QObject, Signal, QTimer

from portfolio_tracker.application.fx import FxService
from portfolio_tracker.application.market_data import MarketDataService
from portfolio_tracker.application.shared.errors import PortfolioTrackerError
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.instrument import InstrumentMetadata
from portfolio_tracker.domain.market_data import MarketPrices, MarketData

from .tasks import TaskRunner


class MarketDataFeed(QObject):
    changed = Signal(object)

    def __init__(
        self,
        task_runner: TaskRunner,
        fx_service: FxService,
        market_data_service: MarketDataService,
        interval: int = 15,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._runner = task_runner
        self._fx_service = fx_service
        self._market_data_service = market_data_service
        self._subscriptions: dict[object, frozenset[InstrumentMetadata]] = {}

        self._is_rates_fetch_running = False
        self._is_prices_fetch_running = False
        self._latest_rates: FxRates | None = None
        self._latest_prices: MarketPrices | None = None
        self._latest_market_data: MarketData | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(interval * 1000)
        self._timer.timeout.connect(self._tick)  # pylint: disable=no-member

    @property
    def latest(self) -> MarketData | None:
        return self._latest_market_data

    @property
    def _is_busy(self) -> bool:
        return self._is_rates_fetch_running or self._is_prices_fetch_running

    def subscribe(
        self, owner: object, instruments: Iterable[InstrumentMetadata]
    ) -> None:
        self._subscriptions[owner] = frozenset(instruments)
        if not self._timer.isActive():
            self._timer.start()
            self._tick()

    def unsubscribe(self, owner: object) -> None:
        self._subscriptions.pop(owner, None)
        if not self._subscriptions:
            self._timer.stop()

    def _tick(self) -> None:
        if self._is_busy:
            return

        instruments: frozenset[InstrumentMetadata] = frozenset().union(
            *self._subscriptions.values()
        )
        self._refresh_rates()
        self._refresh_prices(instruments)
        self._emit()

    def _refresh_rates(self) -> None:
        if rates := self._fx_service.cached_spot_rates:
            self._latest_rates = rates
        else:
            self._runner.start(
                lambda _: self._fx_service.get_spot_rates(),
                on_result=self._on_rates_result,
                on_error=self._on_rates_error,
            )
            self._is_rates_fetch_running = True

    def _refresh_prices(self, instruments: frozenset[InstrumentMetadata]) -> None:
        if prices := self._market_data_service.cached_prices(instruments):
            self._latest_prices = prices
        else:
            self._runner.start(
                lambda _: self._market_data_service.get_spot_prices(instruments),
                on_result=self._on_prices_result,
                on_error=self._on_prices_error,
            )
            self._is_prices_fetch_running = True

    def _on_rates_result(self, rates: FxRates) -> None:
        self._latest_rates = rates
        self._is_rates_fetch_running = False
        self._emit()

    def _on_rates_error(self, _: PortfolioTrackerError) -> None:
        self._is_rates_fetch_running = False
        self._emit()

    def _on_prices_result(self, prices: MarketPrices) -> None:
        self._latest_prices = prices
        self._is_prices_fetch_running = False
        self._emit()

    def _on_prices_error(self, _: PortfolioTrackerError) -> None:
        self._is_prices_fetch_running = False
        self._emit()

    def _emit(self) -> None:
        if self._is_busy or self._latest_rates is None or self._latest_prices is None:
            return

        market_data = MarketData(
            prices=self._latest_prices,
            rates=self._latest_rates,
        )
        if market_data == self._latest_market_data:
            return

        self.changed.emit(market_data)
        self._latest_market_data = market_data
