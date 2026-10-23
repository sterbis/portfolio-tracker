from PySide6.QtWidgets import QWidget

from .context import GuiContext


class Page(QWidget):
    def __init__(
        self,
        context: GuiContext,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._context = context

    def on_activated(self) -> None: ...
    def on_deactivated(self) -> None: ...
    def on_data_changed(self) -> None: ...
    def on_settings_changed(self) -> None: ...
