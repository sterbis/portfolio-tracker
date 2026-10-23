# pylint: disable=no-member

from PySide6.QtCore import QSettings
from PySide6.QtGui import QCloseEvent, QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QListWidget,
    QStackedWidget,
    QHBoxLayout,
)

from .base import Page
from .context import GuiContext
from .portfolio.position.page import PositionsPage


class MainWindow(QMainWindow):
    def __init__(self, context: GuiContext) -> None:
        super().__init__()
        self._context = context
        self._page_factories: list[tuple[str, type[Page]]] = [
            ("Positions", PositionsPage),
        ]
        self._pages: dict[int, Page] = {}
        self._current_page: Page | None = None

        self.setWindowTitle("Portfolio Tracker")
        self.resize(1200, 800)
        self.setMinimumSize(800, 500)

        self._sidebar_list = QListWidget()
        self._sidebar_list.setFixedWidth(180)
        for title, _ in self._page_factories:
            self._sidebar_list.addItem(title)

        self._page_stackedwidget = QStackedWidget()

        central_widget = QWidget()
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._sidebar_list)
        layout.addWidget(self._page_stackedwidget, 1)
        self.setCentralWidget(central_widget)

        self._create_actions()
        self.statusBar().showMessage("Ready")
        self._restore_geometry()

        self._sidebar_list.currentRowChanged.connect(self._on_page_selected)
        self._sidebar_list.setCurrentRow(0)

    def notify_data_changed(self) -> None:
        for page in self._pages.values():
            page.on_data_changed()

    def notify_settings_changed(self) -> None:
        for page in self._pages.values():
            page.on_settings_changed()

    def _create_actions(self) -> None:
        # temporary, until the sync UI exists: simulates "a sync finished"
        data_menu = self.menuBar().addMenu("&Data")
        reload_action = QAction("&Reload data", self)
        reload_action.setShortcut("F5")
        reload_action.triggered.connect(self.notify_data_changed)
        data_menu.addAction(reload_action)

    def _on_page_selected(self, row: int) -> None:
        if row < 0:
            return

        page = self._pages.get(row)
        if page is None:
            _, factory = self._page_factories[row]
            page = factory(self._context)
            self._pages[row] = page
            self._page_stackedwidget.addWidget(page)

        if self._current_page is not None:
            self._current_page.on_deactivated()

        self._page_stackedwidget.setCurrentWidget(page)
        self._current_page = page
        page.on_activated()

    def _restore_geometry(self) -> None:
        geometry = QSettings().value("main_window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._current_page is not None:
            self._current_page.on_deactivated()

        QSettings().setValue("main_window/geometry", self.saveGeometry())
        super().closeEvent(event)
