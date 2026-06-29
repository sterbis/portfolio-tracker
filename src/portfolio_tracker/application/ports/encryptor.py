from abc import ABC, abstractmethod


class Encryptor(ABC):
    def __init__(self, encryption_key: str) -> None:
        self._encryption_key = encryption_key

    @abstractmethod
    def encrypt(self, plain_text: str) -> str: ...

    @abstractmethod
    def decrypt(self, encrypted_text: str) -> str: ...
