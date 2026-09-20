from datetime import datetime, timedelta
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from app.config import settings
from app.database import get_session
from app.models import Channel
from app.security import verify_admin_token
from app.crypto import seal
from app import oauth
from app.services import meta

router = APIRouter(prefix="/auth/meta", tags=["instagram-oauth"])


@router.get("/login")
def login(session: Session = Depends(get_session), _: str = Depends(verify_admin_token)):
    if not settings.meta_app_id or not settings.meta_app_secret or not settings.token_encryption_key:
        raise HTTPException(503, "Configure Instagram app credentials and TOKEN_ENCRYPTION_KEY first")
    return oauth.create_attempt("meta", session)


@router.get("/start")
def start(state: str, session: Session = Depends(get_session)):
    return oauth.start_attempt("meta", state, session, meta.authorization_url)


@router.get("/callback")
def callback(request: Request, state: str, code: str | None = None, error: str | None = None,
             session: Session = Depends(get_session)):
    oauth.consume_attempt("meta", state, request, session)
    if error or not code:
        return RedirectResponse(f"{settings.frontend_admin_origin}/channels?error=Instagram+authorization+cancelled")
    result = meta.exchange(code)
    account = meta.identity(result["access_token"])
    external_id = str(account["user_id"])
    channel = session.exec(select(Channel).where(Channel.platform == "instagram", Channel.external_id == external_id)).first()
    if not channel:
        channel = Channel(platform="instagram", external_id=external_id, display_name=account["username"])
    channel.display_name = account["username"]
    channel.access_token = seal(result["access_token"])
    channel.refresh_token = None
    channel.token_expiry = datetime.utcnow() + timedelta(seconds=result["expires_in"])
    channel.scopes = meta.SCOPES
    channel.is_connected = True
    channel.authorized_at = datetime.utcnow()
    session.add(channel)
    session.commit()
    return RedirectResponse(f"{settings.frontend_admin_origin}/channels?" + urlencode({"connected": channel.display_name}))
