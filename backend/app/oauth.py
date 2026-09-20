import hashlib
import secrets
from datetime import datetime, timedelta
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, update
from app.config import settings
from app.models import OAuthAttempt


def create_attempt(provider, session):
    session.exec(delete(OAuthAttempt).where(OAuthAttempt.created_at < datetime.utcnow() - timedelta(minutes=10)))
    state = secrets.token_urlsafe(32)
    session.add(OAuthAttempt(state=state, provider=provider))
    session.commit()
    return {"authorization_url": f"{settings.public_backend_url}/auth/{provider}/start?state={state}"}


def start_attempt(provider, state, session, url_builder):
    nonce = secrets.token_urlsafe(32)
    result = session.exec(update(OAuthAttempt).where(OAuthAttempt.state == state,
        OAuthAttempt.provider == provider, OAuthAttempt.browser_hash == None,
        OAuthAttempt.created_at > datetime.utcnow() - timedelta(minutes=10))
        .values(browser_hash=hashlib.sha256(nonce.encode()).hexdigest()))
    session.commit()
    if result.rowcount != 1:
        raise HTTPException(400, "Invalid or expired connection link; start again")
    response = RedirectResponse(url_builder(state))
    response.set_cookie(f"oauth_{provider}", nonce, httponly=True, secure=settings.public_backend_url.startswith("https:"),
                        samesite="lax", max_age=600, path=f"/auth/{provider}")
    return response


def consume_attempt(provider, state, request, session):
    nonce = request.cookies.get(f"oauth_{provider}", "")
    result = session.exec(delete(OAuthAttempt).where(OAuthAttempt.state == state,
        OAuthAttempt.provider == provider, OAuthAttempt.browser_hash == hashlib.sha256(nonce.encode()).hexdigest(),
        OAuthAttempt.created_at > datetime.utcnow() - timedelta(minutes=10)))
    session.commit()
    if not nonce or result.rowcount != 1:
        raise HTTPException(400, "Invalid OAuth state or browser session; reconnect from admin")
