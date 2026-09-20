from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Header, HTTPException, status
from app.config import settings
import hashlib
import hmac
import secrets
from fastapi import Depends
from sqlmodel import Session
from app.database import get_session
from app.models import TeamUser, AdminUser

_serializer = URLSafeTimedSerializer(settings.admin_session_secret, salt="admin-session")


def create_admin_token(user: AdminUser | None = None) -> str:
    if user is not None:
        return _serializer.dumps({"user": user.username, "admin_id": user.id,
            "version": hashlib.sha256(user.password_hash.encode()).hexdigest()})
    return _serializer.dumps({"user": settings.admin_username})


def verify_admin_token(authorization: str = Header(default=None), session: Session = Depends(get_session)) -> str:
    """Dependency: require a valid `Authorization: Bearer <token>` header
    obtained from POST /admin/login. Team sessions use a separate serializer.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing admin token")
    token = authorization.split(" ", 1)[1]
    try:
        data = _serializer.loads(token, max_age=60 * 60 * 12)  # 12h session
    except (BadSignature, SignatureExpired):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    if "admin_id" in data:
        user = session.get(AdminUser, data["admin_id"])
        if not user or not user.is_active or data.get("version") != hashlib.sha256(user.password_hash.encode()).hexdigest():
            raise HTTPException(401, "Invalid or expired admin session")
        return user.username
    if data.get("user") != settings.admin_username:
        raise HTTPException(401, "Invalid admin session")
    return data["user"]


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"scrypt${salt}${digest}"


def check_password(password, encoded):
    try:
        _, salt, digest = encoded.split("$")
        actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
        return hmac.compare_digest(actual, digest)
    except (ValueError, TypeError):
        return False


def team_serializer():
    return URLSafeTimedSerializer(settings.admin_session_secret, salt="team-session")


def require_user(authorization: str = Header(default=None), session: Session = Depends(get_session)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise ValueError()
        data = team_serializer().loads(authorization[7:], max_age=43200)
        user = session.get(TeamUser, data["id"])
        if not user or not user.is_active or data["version"] != hashlib.sha256(user.password_hash.encode()).hexdigest():
            raise ValueError()
        return user
    except (BadSignature, ValueError, KeyError):
        raise HTTPException(401, "Sign in with your team account")
