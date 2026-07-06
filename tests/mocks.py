from portfolio_tracker.application.encryption import Encryptor


class MockEncryptor(Encryptor):
    def encrypt(self, plain_text: str) -> str:
        return f"encrypted_{plain_text}"

    def decrypt(self, encrypted_text: str) -> str:
        return encrypted_text.replace("encrypted_", "")
