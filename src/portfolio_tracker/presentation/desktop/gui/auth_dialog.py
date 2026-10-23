# pylint: disable=no-member

import logging
from contextlib import contextmanager
from typing import Generator

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QStackedWidget,
    QDialog,
)

from portfolio_tracker.application.shared.errors import (
    InvalidUsernameOrPasswordError,
    UsernameAlreadyExistsError,
    UserNotLoggedInError,
)
from portfolio_tracker.application.user import (
    UserService,
    AuthenticateUserCommand,
    RegisterUserCommand,
)

logger = logging.getLogger(__name__)


class AuthDialog(QDialog):
    def __init__(self, user_service: UserService, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._user_id: str | None = None

        self._stacked_widget = QStackedWidget()
        self._login_page = LoginPage(user_service)
        self._register_page = RegisterPage(user_service)
        self._stacked_widget.addWidget(self._login_page)
        self._stacked_widget.addWidget(self._register_page)

        self._login_page.authenticated.connect(self._finish)
        self._login_page.registration_requested.connect(lambda: self._show(self._register_page))
        self._register_page.registered.connect(self._finish)
        self._register_page.login_requested.connect(lambda: self._show(self._login_page))

        has_users = user_service.has_users()
        self._register_page.set_can_log_in(has_users)
        self._show(self._login_page if has_users else self._register_page)

    def _show(self, page: _AuthPage) -> None:
        self._stacked_widget.setCurrentWidget(page)
        page.focus_first_field()

    def _finish(self, user_id: str) -> None:
        self._user_id = user_id
        self.accept()

    def get_logged_in_user_id(self) -> str:
        if self._user_id is None:
            raise UserNotLoggedInError()

        return self._user_id


class _AuthPage(QWidget):
    def __init__(self, title: str, submit_text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._form_layout = QFormLayout()

        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.hide()

        self._submit_button = QPushButton(submit_text)
        self._submit_button.setDefault(True)
        self._submit_button.clicked.connect(self._on_submit)

        self._switch_button = QPushButton()
        self._switch_button.setFlat(True)
        self._switch_button.setAutoDefault(False)
        self._switch_button.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(title))
        layout.addLayout(self._form_layout)
        layout.addWidget(self._error_label)
        layout.addWidget(self._submit_button)
        layout.addWidget(self._switch_button, alignment=Qt.AlignmentFlag.AlignHCenter)

    def focus_first_field(self) -> None:
        raise NotImplementedError

    def _reset(self) -> None:
        raise NotImplementedError

    def _on_submit(self) -> None:
        raise NotImplementedError

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.show()

    def _clear_error(self) -> None:
        self._error_label.clear()
        self._error_label.hide()

    @staticmethod
    def _create_password_edit() -> QLineEdit:
        edit = QLineEdit()
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        return edit

    @contextmanager
    def _busy(self) -> Generator[None]:
        self._submit_button.setEnabled(False)
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            yield
        finally:
            QGuiApplication.restoreOverrideCursor()
            self._submit_button.setEnabled(True)


class LoginPage(_AuthPage):
    authenticated = Signal(str)
    registration_requested = Signal()

    def __init__(
        self, user_service: UserService, parent: QWidget | None = None
    ) -> None:
        super().__init__("Login", "Login", parent)
        self._user_service = user_service

        self._username_edit = QLineEdit()
        self._password_edit = self._create_password_edit()
        self._form_layout.addRow("Username", self._username_edit)
        self._form_layout.addRow("Password", self._password_edit)

        self._username_edit.returnPressed.connect(self._password_edit.setFocus)
        self._password_edit.returnPressed.connect(self._on_submit)

        self._switch_button.setText("Register")
        self._switch_button.clicked.connect(self.registration_requested)

    def focus_first_field(self) -> None:
        self._username_edit.setFocus()

    def _reset(self) -> None:
        self._username_edit.clear()
        self._password_edit.clear()
        self._clear_error()

    def _on_submit(self) -> None:
        self._clear_error()
        username = self._username_edit.text().strip()
        password = self._password_edit.text()
        if not username or not password:
            self._show_error("Enter your username and password.")
            return

        with self._busy():
            try:
                user_id = self._user_service.authenticate(
                    command=AuthenticateUserCommand(username, password),
                )
            except InvalidUsernameOrPasswordError:
                self._password_edit.clear()
                self._password_edit.setFocus()
                self._show_error("Invalid username or password.")
                return

        self._reset()
        self.authenticated.emit(user_id)


class RegisterPage(_AuthPage):
    registered = Signal(str)
    login_requested = Signal()

    def __init__(
        self, user_service: UserService, parent: QWidget | None = None
    ) -> None:
        super().__init__("Register", "Register", parent)
        self._user_service = user_service

        self._username_edit = QLineEdit()
        self._password_edit = self._create_password_edit()
        self._confirm_password_edit = self._create_password_edit()
        self._form_layout.addRow("Username", self._username_edit)
        self._form_layout.addRow("Password", self._password_edit)
        self._form_layout.addRow("Confirm password", self._confirm_password_edit)

        self._username_edit.returnPressed.connect(self._password_edit.setFocus)
        self._password_edit.returnPressed.connect(self._confirm_password_edit.setFocus)
        self._confirm_password_edit.returnPressed.connect(self._on_submit)

        self._switch_button.setText("Already registered? Log in")
        self._switch_button.clicked.connect(self.login_requested)

    def set_can_log_in(self, can: bool) -> None:
        self._switch_button.setVisible(can)

    def focus_first_field(self) -> None:
        self._username_edit.setFocus()

    def _reset(self) -> None:
        for edit in (self._username_edit, self._password_edit, self._confirm_password_edit):
            edit.clear()

        self._clear_error()

    def _on_submit(self) -> None:
        self._clear_error()
        username = self._username_edit.text().strip()
        password = self._password_edit.text()
        if not username or not password:
            self._show_error("Choose a username and a password.")
            return

        if password != self._confirm_password_edit.text():
            self._confirm_password_edit.clear()
            self._confirm_password_edit.setFocus()
            self._show_error("Passwords do not match.")
            return

        with self._busy():
            try:
                user_id = self._user_service.register(
                    command=RegisterUserCommand(username, password),
                )
            except UsernameAlreadyExistsError:
                self._username_edit.setFocus()
                self._show_error("That username is already taken.")
                return

        self._reset()
        self.registered.emit(user_id)
