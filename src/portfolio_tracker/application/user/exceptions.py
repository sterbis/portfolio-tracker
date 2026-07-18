from portfolio_tracker.application.contracts.exceptions import AppError


class InvalidUsernameOrPasswordError(AppError):
    _message_template = "Invalid username or password."


class UserAlreadyExistsError(AppError):
    _message_template = "User with '{username}' username already exists."

    def __init__(self, username: str) -> None:
        super().__init__(username=username)


class UserAlreadyLoggedOutError(AppError):
    _message_template = "User already logged out."


class UserNotLoggedInError(AppError):
    _message_template = "No user is currently logged in."
