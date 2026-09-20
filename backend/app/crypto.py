from cryptography.fernet import Fernet
from app.config import settings


def seal(value):
    if not value:
        return None
    if not settings.token_encryption_key:
        raise RuntimeError("Set TOKEN_ENCRYPTION_KEY before connecting channels")
    return "enc:" + Fernet(settings.token_encryption_key.encode()).encrypt(value.encode()).decode()


def unseal(value):
    if not value:
        return None
    if not value.startswith("enc:"):
        raise RuntimeError("Legacy plaintext token: reconnect this channel")
    return Fernet(settings.token_encryption_key.encode()).decrypt(value[4:].encode()).decode()
