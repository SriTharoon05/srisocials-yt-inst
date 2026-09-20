from cryptography.fernet import Fernet, InvalidToken
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
    try:
        return Fernet(settings.token_encryption_key.encode()).decrypt(value[4:].encode()).decode()
    except (InvalidToken, ValueError):
        raise RuntimeError("Cannot decrypt channel credentials. Use the same TOKEN_ENCRYPTION_KEY locally and on Render, then reconnect this channel.") from None
