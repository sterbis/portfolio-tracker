from typing import Any, Sequence


from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QTableView,
    QAbstractItemView,
)

from portfolio_tracker.application.portfolio import PositionsResult, GetPositionsQuery, BuildPortfolioSnapshotQuery, ViewPortfolioSnapshotQuery
from portfolio_tracker.application.views import PositionRowView
from portfolio_tracker.domain.instrument import InstrumentMetadata
from portfolio_tracker.domain.market_data import MarketData
from portfolio_tracker.presentation.desktop.gui.base import Page
from portfolio_tracker.presentation.desktop.gui.context import GuiContext
from portfolio_tracker.presentation.desktop.gui.filters import FilterBar
from portfolio_tracker.presentation.shared.tables import ColumnSpec, get_table_spec
from portfolio_tracker.presentation.shared.settings import DisplaySettings
from portfolio_tracker.settings import Settings

from .presenter import PositionsPresenter
from .model import SpecTableModel


class TotalsBar(QWidget):
    def __init__(
        self,
        column_specs: Sequence[ColumnSpec],
        display_settings: DisplaySettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._display_settings = display_settings
        self._total_view: Any | None = None
        self._labels: list[tuple[ColumnSpec, QLabel]] = []
        self._layout = QHBoxLayout(self)
        self.configure(column_specs, display_settings)

    def configure(
        self, column_specs: Sequence[ColumnSpec], display_settings: DisplaySettings
    ) -> None:
        self._display_settings = display_settings
        while (item := self._layout.takeAt(0)) is not None:
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._labels = []
        for column_spec in column_specs:
            if column_spec.total_field is not None:
                label = QLabel()
                self._labels.append((column_spec, label))
                self._layout.addWidget(label)

        self._layout.addStretch(1)
        self.setVisible(bool(self._labels))
        self._render()

    def set_totals(self, total_view: Any) -> None:
        self._total_view = total_view
        self._render()

    def _render(self) -> None:
        for column_spec, label in self._labels:
            value = (
                column_spec.get_total_value(self._total_view)
                if self._total_view is not None
                else None
            )
            label.setText(
                f"{column_spec.title}: {column_spec.format_value(value, self._display_settings)}"
            )


class PositionsPage(Page):
    def __init__(
        self,
        context: GuiContext,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(context, parent)
        self._table_spec = get_table_spec(PositionRowView)
        self._is_active = False
        self._is_dirty = False

        settings = context.settings_cache.get(context.user_id)
        display_settings = settings.display.gui
        column_specs = self._active_column_specs(settings)

        self._presenter = PositionsPresenter(context, self)
        self._model = SpecTableModel(column_specs, PositionRowView, display_settings, parent=self)

        self._filter_bar = FilterBar(
            self._table_spec,
            PositionRowView,
            self._default_query(settings),
            self,
        )
        self._table_view = QTableView()
        self._setup_table_view()
        self._totals_bar = TotalsBar(column_specs, display_settings, self)

        self._message_label = QLabel()
        self._message_label.setTextFormat(Qt.TextFormat.PlainText)
        self._message_label.setWordWrap(True)
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.hide()

        layout = QVBoxLayout(self)
        layout.addWidget(self._filter_bar)
        layout.addWidget(self._message_label)
        layout.addWidget(self._table_view, 1)
        layout.addWidget(self._totals_bar)

        self._connect_signals()

    def on_activated(self) -> None:
        self._is_active = True
        market_data_feed = self._context.market_data_feed
        market_data_feed.subscribe(self, self._presenter.instruments)
        self._presenter.refresh(self._filter_bar.applied_query, force=self._is_dirty)
        self._is_dirty = False
        if (latest := market_data_feed.latest) is not None:
            self._presenter.refresh_market_data(latest)

    def on_deactivated(self) -> None:
        self._is_active = False
        self._context.market_data_feed.unsubscribe(self)

    def on_data_changed(self) -> None:
        if self._is_active:
            self._presenter.refresh(self._filter_bar.applied_query, force=True)
        else:
            self._is_dirty = True

    def on_settings_changed(self) -> None:
        settings = self._context.settings_cache.get(self._context.user_id)
        display_settings = settings.display.gui
        column_specs = self._active_column_specs(settings)
        self._model.configure(column_specs, display_settings)
        self._filter_bar.set_default_query(self._default_query(settings))
        self._table_view.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self._totals_bar.configure(column_specs, display_settings)
        if self._is_active:
            self._presenter.refresh(self._filter_bar.applied_query)

    def _setup_table_view(self) -> None:
        view = self._table_view
        view.setModel(self._model)
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        view.setAlternatingRowColors(True)
        view.verticalHeader().hide()
        view.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        view.setSortingEnabled(True)

    def _connect_signals(self) -> None:
        self._filter_bar.refresh_requested.connect(self._presenter.refresh)
        self._presenter.loading_changed.connect(self._on_loading_changed)
        self._presenter.positions_changed.connect(self._on_positions_changed)
        self._presenter.instruments_changed.connect(self._on_instruments_changed)
        self._presenter.failed.connect(self._on_failed)
        self._context.market_data_feed.changed.connect(self._on_market_data_changed)

    def _active_column_specs(self, settings: Settings) -> list[ColumnSpec]:
        table_settings = settings.display.gui.tables[self._table_spec.name]
        return [
            self._table_spec.columns[column_name]
            for column_name in table_settings.active_columns
            if column_name in self._table_spec.columns
        ]

    @staticmethod
    def _default_query(settings: Settings) -> GetPositionsQuery:
        return GetPositionsQuery(
            build=BuildPortfolioSnapshotQuery(
                reporting_currency=settings.application.reporting_currency,
                accounting_method=settings.application.accounting_method,
            ),
            view=ViewPortfolioSnapshotQuery(
                scope_type=settings.application.consolidation_scope_type,
            ),
        )

    def _on_loading_changed(self, loading: bool) -> None:
        self._filter_bar.set_busy(loading)
        if loading:
            self.setCursor(Qt.CursorShape.BusyCursor)
            if self._model.rowCount() == 0:
                self._show_message("Loading…")
        else:
            self.unsetCursor()

    def _on_positions_changed(self, result: PositionsResult) -> None:
        self._model.set_rows(result.positions)
        self._totals_bar.set_totals(result.totals)
        if result.positions:
            self._message_label.hide()
            return

        query = self._filter_bar.applied_query
        no_filter = query.view.options.filter is None and query.build.as_of is None
        if no_filter:
            self._show_message("No positions match the filter.")
        else:
            self._show_message("No positions yet. Run a sync to import your data.")

    def _on_instruments_changed(
        self, instruments: frozenset[InstrumentMetadata]
    ) -> None:
        if self._is_active:
            self._context.market_data_feed.subscribe(self, instruments)

    def _on_market_data_changed(self, market_data: MarketData) -> None:
        if self._is_active:
            self._presenter.refresh_market_data(market_data)

    def _on_failed(self, message: str) -> None:
        self._show_message(f"Could not load positions: {message}")

    def _show_message(self, text: str) -> None:
        self._message_label.setText(text)
        self._message_label.show()
