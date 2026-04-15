from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets
import base64

from os.path import exists # noqa
from pathlib import Path

class Coder:
    def __init__(self) -> None:
        pass


    @staticmethod
    def generateSalt(path: Path, bytesLength: int = 128):
        open(path.absolute(), "wb").write(secrets.token_bytes(bytesLength))

    @staticmethod
    def loadSalt(path: Path):
        return open(path.absolute(), "rb").read()

    def createKey(self, path: Path, password: str) -> bytes:
        if not exists(path.absolute()): self.generateSalt(path)
        salt = self.loadSalt(path)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=500000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    @staticmethod
    def decryptDataFromFile(path: Path, key: bytes) -> bytes:
        return Fernet(key).decrypt(open(path.absolute(), "rb").read())

    @staticmethod
    def encryptDataFromFile(path: Path, key: bytes) -> bytes:
        return Fernet(key).encrypt(open(path.absolute(), "rb").read())

    def encryptFile(self, path: Path, password:str):
        key: bytes = self.createKey(path.parent.absolute() / "salt", password)
        filePath: path = path

        contents: bytes = self.encryptDataFromFile(path, key) # The already encrypted data

        with open(filePath.absolute(), "wb") as file:
            file.write(contents)

    def decryptFile(self, path: Path, password: str):
        key: bytes = self.createKey(path.parent.absolute() / "salt", password)
        filePath: path = path

        contents: bytes = self.decryptDataFromFile(path, key) # The already decrypted data
        with open(filePath.absolute(), "wb") as file:
            file.write(contents)

if __name__ == '__main__':
    coder = Coder()
    password = "peeta"
    path = Path("/Users/pietrobellizio/PycharmProjects/EmailRelay/credentials.enc")
    coder.encryptFile(path, password)