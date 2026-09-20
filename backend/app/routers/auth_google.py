from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session
from datetime import datetime

from app.database import get_session
from app.models import Channel
from app.services import youtube as yt_service
from app.security import verify_admin_token
from app.config import settings
from app import oauth
from app.crypto import seal
from urllib.parse import urlencode

router = APIRouter(prefix="/auth/google", tags=["google-oauth"])


@router.get("/login")
def login(_: str = Depends(verify_admin_token), session: Session = Depends(get_session)):
    """Admin-only: kick off consent screen for connecting ONE more YouTube channel.
    You'll call this once per channel (5 times total), logging into the matching
    Google/Brand Account each time in the browser before approving."""
    if not settings.google_client_id or not settings.google_client_secret or not settings.token_encryption_key:
        raise HTTPException(503, "Configure Google credentials and TOKEN_ENCRYPTION_KEY")
    return oauth.create_attempt("google", session)


def authorization_url(state):
    flow = yt_service.build_flow(state)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


@router.get("/start")
def start(state: str, session: Session = Depends(get_session)):
    return oauth.start_attempt("google", state, session, authorization_url)


@router.get("/callback")
def callback(request: Request, code: str | None = None, state: str = Query(...), error: str | None = None,
             session: Session = Depends(get_session)):
    """Google redirects here after consent. We exchange the code for tokens,
    identify which channel it is, and upsert a Channel row for it."""
    oauth.consume_attempt("google", state, request, session)
    if error or not code:
        return RedirectResponse(f"{settings.frontend_admin_origin}/channels?error=Google+authorization+cancelled")
    flow = yt_service.build_flow(state=state)
    try:
        flow.fetch_token(code=code)
    except Exception:
        raise HTTPException(400, "Google token exchange failed; reconnect and grant both required scopes")
    creds = flow.credentials

    identity = yt_service.fetch_channel_identity(creds)
    if not identity:
        raise HTTPException(400, "Could not read YouTube channel for this account")

    channel = session.query(Channel).filter(
        Channel.platform == "youtube",
        Channel.external_id == identity["external_id"],
    ).first()

    if not channel:
        channel = Channel(platform="youtube", external_id=identity["external_id"],
                           display_name=identity["title"])

    channel.display_name = identity["title"]
    channel.access_token = seal(creds.token)
    channel.refresh_token = seal(creds.refresh_token) or channel.refresh_token
    channel.token_expiry = creds.expiry
    channel.scopes = ",".join(creds.scopes or [])
    channel.is_connected = True
    channel.authorized_at = datetime.utcnow()

    session.add(channel)
    session.commit()

    # Send the admin back to the dashboard's "channels" screen
    return RedirectResponse(f"{settings.frontend_admin_origin}/channels?" + urlencode({"connected": identity['title']}))
