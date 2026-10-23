# pylint: disable=no-member

from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Mapping, cast

from PySide6.QtCore import Signal, QDate, Qt
from PySide6.QtWidgets import (
    QWidget,
    QComboBox,
    QLineEdit,
    QDateEdit,
    QStackedWidget,
    QToolButton,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QCheckBox,
)

from filterutils import Operator, Filter, FilterNode, FilterTree

from portfolio_tracker.application.portfolio import (
    GetPositionsQuery,
    BuildPortfolioSnapshotQuery,
    ViewPortfolioSnapshotQuery,
)
from portfolio_tracker.application.shared.service import QueryOptions
from portfolio_tracker.application.views import MoneyView
from portfolio_tracker.domain.portfolio import ScopeType
from portfolio_tracker.domain.portfolio.position import AccountingMethod
from portfolio_tracker.domain.shared import Currency
from portfolio_tracker.presentation.shared.tables import (
    ColumnKind,
    ColumnSpec,
    TableSpec,
)


class FilterInputError(ValueError): ...


KIND_OPERATORS: dict[ColumnKind, tuple[tuple[Operator, str], ...]] = {
    ColumnKind.TEXT: (
        (Operator.LIKE, "contains"),
        (Operator.NOT_LIKE, "does not contain"),
        (Operator.EQ, "is"),
        (Operator.NE, "is not"),
        (Operator.IN, "is any of"),
        (Operator.NOT_IN, "is none of"),
        (Operator.LIKE_ANY, "contains any of"),
    ),
    **{
        kind: (
            (Operator.EQ, "="),
            (Operator.NE, "≠"),
            (Operator.GT, ">"),
            (Operator.GE, "≥"),
            (Operator.LT, "<"),
            (Operator.LE, "≤"),
        )
        for kind in (ColumnKind.NUMBER, ColumnKind.MONEY, ColumnKind.PERCENT)
    },
    ColumnKind.DATETIME: ((Operator.GE, "on or after"), (Operator.LT, "before")),
}
LIST_OPERATORS = {Operator.IN, Operator.NOT_IN, Operator.LIKE_ANY}


def _to_decimal(text: str) -> Decimal:
    try:
        value = Decimal(text.replace(",", "."))
    except InvalidOperation:
        raise FilterInputError("Enter a number") from None
    if not value.is_finite():
        raise FilterInputError("Enter a number")
    return value


def parse_filter_value(
    kind: ColumnKind, operator: Operator, text: str, *, reporting_currency: Currency
) -> Any:
    text = text.strip()
    if not text:
        raise FilterInputError("Enter a value")
    if operator in LIST_OPERATORS:
        return [value.strip() for value in text.split(",") if value.strip()]
    match kind:
        case ColumnKind.TEXT:
            return text
        case ColumnKind.NUMBER:
            return _to_decimal(text)
        case ColumnKind.MONEY:
            return MoneyView(_to_decimal(text), reporting_currency)
        case ColumnKind.PERCENT:
            return _to_decimal(text) / 100

    raise AssertionError(kind)


class FilterWidget(QWidget):
    remove_requested = Signal(object)
    apply_requested = Signal()

    def __init__(
        self, column_specs: Mapping[str, ColumnSpec], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._column_specs = column_specs
        self._current_kind: ColumnKind | None = None

        self._column_combobox = QComboBox()
        self._column_combobox.setPlaceholderText("Column")
        for column_name, column_spec in column_specs.items():
            self._column_combobox.addItem(column_spec.title, column_name)

        self._column_combobox.setCurrentIndex(-1)

        self._operator_combobox = QComboBox()
        self._operator_combobox.setEnabled(False)

        self._text_edit = QLineEdit()
        self._date_edit = QDateEdit(QDate.currentDate())
        self._date_edit.setCalendarPopup(True)

        self._value_stackedwidget = QStackedWidget()
        self._value_stackedwidget.addWidget(self._text_edit)
        self._value_stackedwidget.addWidget(self._date_edit)

        self._remove_button = QToolButton()
        self._remove_button.setText("✕")
        self._remove_button.setToolTip("Remove filter")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._column_combobox)
        layout.addWidget(self._operator_combobox)
        layout.addWidget(self._value_stackedwidget)
        layout.setStretchFactor(self._value_stackedwidget, 1)
        layout.addWidget(self._remove_button)

        self._column_combobox.currentIndexChanged.connect(self._on_column_changed)
        self._operator_combobox.currentIndexChanged.connect(self._update_text_edit_placeholder)
        self._text_edit.returnPressed.connect(self.apply_requested)
        self._remove_button.clicked.connect(lambda: self.remove_requested.emit(self))

    def is_blank(self) -> bool:
        return self._current_kind is None and not self._text_edit.text().strip()

    def set_error(self, message: str | None) -> None:
        self.setToolTip(message or "")
        self.setStyleSheet(
            "QLineEdit, QComboBox { border: 1px solid #c0392b; }" if message else ""
        )

    def to_filter(
        self, item_type: type, reporting_currency: Currency
    ) -> FilterNode:
        if self._current_kind is None:
            raise FilterInputError("Select a column")

        column_spec = self._column_specs[self._column_combobox.currentData()]
        operator = Operator(self._operator_combobox.currentData())

        if self._current_kind is ColumnKind.DATETIME:
            value = datetime.combine(
                cast(date, self._date_edit.date().toPython()), time.min
            ).astimezone(timezone.utc)

        else:
            value = parse_filter_value(
                self._current_kind,
                operator,
                self._text_edit.text(),
                reporting_currency=reporting_currency,
            )

        return FilterNode(
            field=column_spec.field, operator=operator, value=value, item_type=item_type
        )

    def _on_column_changed(self, _index: int) -> None:
        column_name = self._column_combobox.currentData()
        if column_name is None:
            return

        self._current_kind = self._column_specs[column_name].kind

        self._operator_combobox.clear()
        for operator, label in KIND_OPERATORS[self._current_kind]:
            self._operator_combobox.addItem(label, operator.value)

        self._operator_combobox.setEnabled(True)

        if self._current_kind is ColumnKind.DATETIME:
            self._value_stackedwidget.setCurrentWidget(self._date_edit)
        else:
            self._value_stackedwidget.setCurrentWidget(self._text_edit)
            self._update_text_edit_placeholder()

        self._text_edit.clear()
        self.set_error(None)

    def _update_text_edit_placeholder(self) -> None:
        operator_value = self._operator_combobox.currentData()
        if operator_value is not None and Operator(operator_value) in LIST_OPERATORS:
            self._text_edit.setPlaceholderText("Comma separated values (AAPL, MSFT, GOOGL)")
        elif self._current_kind is ColumnKind.PERCENT:
            self._text_edit.setPlaceholderText("Percent value")
        else:
            self._text_edit.setPlaceholderText("Value")


class FilterPanel(QWidget):
    apply_requested = Signal()

    def __init__(
        self, column_specs: Mapping[str, ColumnSpec], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._column_specs = column_specs
        self._filter_widgets: list[FilterWidget] = []

        self._toggle_button = QToolButton()
        self._toggle_button.setCheckable(True)
        self._toggle_button.setChecked(True)
        self._toggle_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )

        self._add_filter_button = QPushButton("+ Add filter")

        self._container_widget = QWidget()
        self._container_layout = QVBoxLayout(self._container_widget)
        self._container_layout.setContentsMargins(0, 0, 0, 0)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self._toggle_button)
        top_layout.addStretch(1)
        top_layout.addWidget(self._add_filter_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_layout)
        layout.addWidget(self._container_widget)

        self._toggle_button.toggled.connect(self._container_widget.setVisible)
        self._add_filter_button.clicked.connect(self.add_filter)
        self._update_toggle_button()

    def add_filter(self) -> None:
        widget = FilterWidget(self._column_specs, self)
        widget.remove_requested.connect(self._remove_filter)
        widget.apply_requested.connect(self.apply_requested)
        self._filter_widgets.append(widget)
        self._container_layout.addWidget(widget)
        self._toggle_button.setChecked(True)
        self._update_toggle_button()

    def clear(self) -> None:
        for widget in list(self._filter_widgets):
            self._remove_filter(widget)

    def build_filter(
        self, item_type: type, reporting_currency: Currency
    ) -> Filter | None:
        filters: list[FilterNode] = []
        invalid = False
        for widget in self._filter_widgets:
            widget.set_error(None)
            if widget.is_blank():
                continue
            try:
                filters.append(widget.to_filter(item_type, reporting_currency))
            except FilterInputError as error:
                widget.set_error(str(error))
                invalid = True
        if invalid:
            raise FilterInputError("Fix the highlighted filters")
        if not filters:
            return None
        return filters[0] if len(filters) == 1 else FilterTree(*filters)

    def _remove_filter(self, widget: FilterWidget) -> None:
        self._filter_widgets.remove(widget)
        self._container_layout.removeWidget(widget)
        widget.deleteLater()
        self._update_toggle_button()

    def _update_toggle_button(self) -> None:
        count = len(self._filter_widgets)
        self._toggle_button.setText(f"Filters ({count})" if count else "Filters")
        self._toggle_button.setArrowType(
            Qt.ArrowType.DownArrow
            if self._toggle_button.isChecked()
            else Qt.ArrowType.RightArrow
        )


class FilterBar(QWidget):
    refresh_requested = Signal(object)  # GetPositionsQuery

    def __init__(
        self,
        table_spec: TableSpec[Any],
        item_type: type,
        default_query: GetPositionsQuery,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._item_type = item_type
        self._default_query = default_query

        self._currency_combobox = self._enum_combobox(Currency)
        self._accounting_combobox = self._enum_combobox(AccountingMethod)
        self._scope_combobox = self._enum_combobox(ScopeType)

        self._as_of_checkbox = QCheckBox("As of")
        self._as_of_edit = QDateEdit(QDate.currentDate())
        self._as_of_edit.setCalendarPopup(True)
        self._as_of_edit.setMaximumDate(QDate.currentDate())

        self._filter_panel = FilterPanel(table_spec.columns, self)

        self._reset_button = QPushButton("Reset")
        self._apply_button = QPushButton("Apply")

        self._error_label = QLabel()
        self._error_label.hide()

        top_layout = QHBoxLayout()
        top_layout.addWidget(self._currency_combobox)
        top_layout.addWidget(self._accounting_combobox)
        top_layout.addWidget(self._as_of_checkbox)
        top_layout.addWidget(self._as_of_edit)
        top_layout.addWidget(self._scope_combobox)
        top_layout.addStretch(1)
        top_layout.addWidget(self._reset_button)
        top_layout.addWidget(self._apply_button)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self._filter_panel)
        layout.addWidget(self._error_label)

        self._as_of_checkbox.toggled.connect(self._as_of_edit.setEnabled)
        self._apply_button.clicked.connect(self._on_apply)
        self._reset_button.clicked.connect(self._on_reset)
        self._filter_panel.apply_requested.connect(self._on_apply)

        self._restore_defaults()
        self._applied_query = self._build_query()

    @property
    def applied_query(self) -> GetPositionsQuery:
        return self._applied_query

    def set_default_query(self, default_query: GetPositionsQuery) -> None:
        was_at_defaults = self._applied_query == self._default_query
        self._default_query = default_query
        if was_at_defaults:
            self._restore_defaults()
            self._applied_query = self._build_query()

    def set_busy(self, busy: bool) -> None:
        self.setEnabled(not busy)

    @staticmethod
    def _enum_combobox[E: StrEnum](enum_cls: type[E]) -> QComboBox:
        combobox = QComboBox()
        for member in enum_cls:
            combobox.addItem(
                (
                    member.value.replace("_", " ").title()
                    if len(member.value) > 3
                    else member.value
                ),
                member.value,
            )
        return combobox

    @staticmethod
    def _select(combobox: QComboBox, value: StrEnum) -> None:
        combobox.setCurrentIndex(combobox.findData(value.value))

    def _restore_defaults(self) -> None:
        build_query, view_query = self._default_query.build, self._default_query.view
        self._select(self._currency_combobox, build_query.reporting_currency)
        self._select(self._accounting_combobox, build_query.accounting_method)
        self._select(self._scope_combobox, view_query.scope_type)
        as_of = build_query.as_of
        self._as_of_checkbox.setChecked(as_of is not None)
        self._as_of_edit.setEnabled(as_of is not None)
        self._as_of_edit.setDate(
            QDate(as_of.year, as_of.month, as_of.day) if as_of else QDate.currentDate()
        )
        self._filter_panel.clear()

    def _build_query(self) -> GetPositionsQuery:
        reporting_currency = Currency(self._currency_combobox.currentData())
        as_of = (
            cast(date, self._as_of_edit.date().toPython())
            if self._as_of_checkbox.isChecked()
            else None
        )
        accounting_method = AccountingMethod(self._accounting_combobox.currentData())
        scope_type = ScopeType(self._scope_combobox.currentData())
        filter_ = self._filter_panel.build_filter(self._item_type, reporting_currency)

        return GetPositionsQuery(
            build=BuildPortfolioSnapshotQuery(
                reporting_currency=reporting_currency,
                as_of=as_of,
                accounting_method=accounting_method,
            ),
            view=ViewPortfolioSnapshotQuery(
                scope_type=scope_type,
                options=QueryOptions(filter=filter_),
            ),
        )

    def _on_apply(self) -> None:
        try:
            query = self._build_query()
        except FilterInputError as error:
            self._error_label.setText(str(error))
            self._error_label.show()
        else:
            self._error_label.hide()
            self._applied_query = query
            self.refresh_requested.emit(query)

    def _on_reset(self) -> None:
        self._restore_defaults()
        self._on_apply()
