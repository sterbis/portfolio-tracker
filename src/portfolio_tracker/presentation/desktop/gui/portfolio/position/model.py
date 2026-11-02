from typing import Any, Hashable, Sequence, Protocol

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    Qt,
    QPersistentModelIndex,
)
from PySide6.QtGui import QColor

from portfolio_tracker.application.shared.sort import Sort
from portfolio_tracker.application.views import MoneyView
from portfolio_tracker.presentation.shared.tables import (
    ColumnSpec,
    HorizontalAlignment,
    Tone,
)
from portfolio_tracker.presentation.shared.settings import DisplaySettings

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


class RowObject(Protocol):
    @property
    def key(self) -> Hashable: ...


class SpecTableModel(QAbstractTableModel):
    def __init__(
        self,
        column_specs: Sequence[ColumnSpec],
        object_class: type,
        settings: DisplaySettings,
        sorts: tuple[Sort, ...] = (),
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._column_specs = column_specs
        self._object_class = object_class
        self._display_settings = settings
        self._sorts = sorts
        self._rows: list[RowObject] = []
        self._sorted_rows: list[RowObject] = []
        self._sorted_row_keys: list[Hashable] = []

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

        obj = self._sorted_rows[index.row()]
        value = column_spec.get_value(obj)

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
        self._sorts = ()
        self.endResetModel()

    def set_rows(self, rows: Sequence[RowObject]) -> None:
        self._rows = list(rows)
        sorted_rows = Sort.apply_many(self._rows, self._sorts)
        sorted_row_keys = [row.key for row in sorted_rows]

        if sorted_row_keys == self._sorted_row_keys:
            if not rows or not self._column_specs:
                return

            self._sorted_rows = sorted_rows
            self.dataChanged.emit(  # pylint: disable=no-member
                self.index(0, 0),
                self.index(len(rows) - 1, len(self._column_specs) - 1)
            )

        else:
            self.beginResetModel()
            self._sorted_rows = sorted_rows
            self._sorted_row_keys = sorted_row_keys
            self.endResetModel()

    def row_by_index(self, index: int) -> RowObject:
        return self._sorted_rows[index]

    def row_by_key(self, key: Hashable) -> int | None:
        try:
            return self._sorted_row_keys.index(key)
        except ValueError:
            return None

    def sort(self, column_index: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if 0 <= column_index < len(self._column_specs):
            field_path = self._column_specs[column_index].field_path
            reverse = order == Qt.SortOrder.DescendingOrder
            self._sorts = (Sort(field_path, self._object_class, reverse), )
        else:
            self._sorts = ()

        self.beginResetModel()
        self._sorted_rows = Sort.apply_many(self._rows, self._sorts)
        self._sorted_row_keys = [row.key for row in self._sorted_rows]
        self.endResetModel()
