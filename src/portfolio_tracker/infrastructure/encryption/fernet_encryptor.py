from cryptography.fernet import Fernet

from portfolio_tracker.application.ports.encryptor import Encryptor


class FernetEncryptor(Encryptor):
    def __init__(self, encryption_key: str):
        super().__init__(encryption_key)
        self._fernet = Fernet(self._encryption_key.encode())

    def encrypt(self, plain_text: str) -> str:
        return self._fernet.encrypt(plain_text.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        return self._fernet.decrypt(encrypted_text.encode()).decode()
