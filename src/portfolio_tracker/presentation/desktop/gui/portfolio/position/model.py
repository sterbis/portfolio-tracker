from typing import Any, Hashable, Sequence, Protocol

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    Qt,
    QPersistentModelIndex,
)
from PySide6.QtGui import QColor

from portfolio_tracker.application.views import MoneyView
from portfolio_tracker.presentation.shared.tables import (
    ColumnSpec,
    HorizontalAlignment,
    Tone,
)
from portfolio_tracker.settings import DisplaySettings

QT_ALIGNMENTS = {
    HorizontalAlignment.LEFT: Qt.AlignmentFlag.AlignLeft
    | Qt.AlignmentFlag.AlignVCenter,
    HorizontalAlignment.RIGHT: Qt.AlignmentFlag.AlignRight
    | Qt.AlignmentFlag.AlignVCenter,
    HorizontalAlignment.CENTER: Qt.AlignmentFlag.AlignHCenter
    | Qt.AlignmentFlag.AlignVCenter,
}


def cell_foreground_color(value: Any, column_spec: ColumnSpec) -> QColor | None:
    if value is None:
        return None

    if column_spec.tone == Tone.PROFIT_OR_LOSS:
        amount = value.amount if isinstance(value, MoneyView) else value
        if amount > 0:
            return QColor("#2e7d32")
        if amount < 0:
            return QColor("#c62828")

    return None


class RowView(Protocol):
    @property
    def key(self) -> Hashable: ...


class SpecTableModel(QAbstractTableModel):
    def __init__(
        self,
        column_specs: Sequence[ColumnSpec],
        settings: DisplaySettings,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._column_specs = column_specs
        self._display_settings = settings
        self._rows: list[RowView] = []
        self._row_keys: list[Hashable] = []
        self._sort: tuple[int, Qt.SortOrder] | None = None

    def rowCount(
        self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()
    ) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(
        self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()
    ) -> int:
        return 0 if parent.isValid() else len(self._column_specs)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None

        column_spec = self._column_specs[index.column()]

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return QT_ALIGNMENTS.get(column_spec.horizontal_alignment)
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ForegroundRole):
            return None

        view = self._rows[index.row()]
        value = column_spec.get_value(view)

        if role == Qt.ItemDataRole.DisplayRole:
            return column_spec.format_value(value, self._display_settings)
        if role == Qt.ItemDataRole.ForegroundRole:
            return cell_foreground_color(value, column_spec)
        if role == Qt.ItemDataRole.UserRole:
            return value

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self._column_specs[section].title

        return None

    def configure(self, column_specs: Sequence[ColumnSpec], display_settings: DisplaySettings) -> None:
        self.beginResetModel()
        self._column_specs = list(column_specs)
        self._display_settings = display_settings
        self._sort = None
        self.endResetModel()

    def set_rows(self, rows: Sequence[RowView]) -> None:
        row_keys = [row.key for row in rows]

        if row_keys == self._row_keys:
            if not rows or not self._column_specs:
                return

            self._rows = list(rows)
            self.dataChanged.emit(  # pylint: disable=no-member
                self.index(0, 0),
                self.index(len(rows) - 1, len(self._column_specs) - 1)
            )

        else:
            self.beginResetModel()
            self._rows = list(rows)
            self._row_keys = row_keys
            self.endResetModel()

    def row_by_index(self, index: int) -> RowView:
        return self._rows[index]

    def row_by_key(self, key: Hashable) -> int | None:
        try:
            return self._row_keys.index(key)
        except ValueError:
            return None

    def sort(self, column_index: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        self._sort = (column_index, order) if column_index >= 0 else None
        self.beginResetModel()
        self._rows = self._sorted(self._rows)
        self._row_keys = [row.key for row in self._rows]
        self.endResetModel()

    def _sorted(self, rows: Sequence[RowView]) -> list[RowView]:
        if self._sort is None or not 0 <= self._sort[0] < len(self._column_specs):
            return list(rows)

        column_spec = self._column_specs[self._sort[0]]
        reverse = self._sort[1] == Qt.SortOrder.DescendingOrder

        def sort_value(row: RowView) -> Any:
            value = column_spec.get_value(row)
            value = getattr(value, "amount", value)          # unwrap MoneyView
            return value.casefold() if isinstance(value, str) else value

        keyed = [(sort_value(row), row) for row in rows]
        present = sorted((p for p in keyed if p[0] is not None), key=lambda p: p[0], reverse=reverse)
        missing = [p for p in keyed if p[0] is None]
        return [row for _, row in present] + [row for _, row in missing]
