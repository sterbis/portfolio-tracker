from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterUserCommand:
    username: str
    password: str


@dataclass(frozen=True)
class AuthenticateUserCommand:
    username: str
    password: str
