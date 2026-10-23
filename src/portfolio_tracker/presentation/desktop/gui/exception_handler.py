import logging
import sys
import threading
import traceback
from pathlib import Path
from types import TracebackType

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMessageBox

logger = logging.getLogger(__name__)


class ExceptionHandler(QObject):
    _handle = Signal(object, object, object)

    def __init__(self, app: QApplication, log_file: Path):
        super().__init__(app)
        self._app = app
        self._log_file = log_file
        self._handling = False
        self._handle.connect(self._show)

    def install(self) -> None:
        sys.excepthook = self._on_exception
        threading.excepthook = lambda args: self._on_exception(
            args.exc_type, args.exc_value, args.exc_traceback # type: ignore
        )

    def _on_exception(
        self,
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return

        logger.critical("Unexpected critical error", exc_info=(exc_type, exc, tb))
        self._handle.emit(exc_type, exc, tb)

    def _show(
        self,
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        if self._handling:
            return

        self._handling = True
        try:
            messagebox = QMessageBox(
                QMessageBox.Icon.Critical,
                "Unexpected Critical Error",
                "Unexpected critical error occurred. Portfolio Tracker will close.",
                QMessageBox.StandardButton.Close,
                parent=self._app.activeWindow(),
            )
            messagebox.setInformativeText(
                f"Please check application log for more details:\n{self._log_file}"
            )
            messagebox.setDetailedText("".join(traceback.format_exception(exc_type, exc, tb)))
            messagebox.exec()

        finally:
            self._app.exit(1)


def install_exception_handler(app: QApplication, log_file: Path) -> None:
    ExceptionHandler(app, log_file).install()
