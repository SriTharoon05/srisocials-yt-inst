from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Channel
from app.security import verify_admin_token, require_user
from app.models import TeamUser, Video
from app.services import storage
from app.crypto import unseal
from datetime import datetime
from datetime import date, timedelta
import httpx

router = APIRouter(tags=["channels"])


@router.get("/admin/channels/{channel_id}/analytics")
def channel_analytics(channel_id: int, start_date: date | None = None, end_date: date | None = None,
                      session: Session = Depends(get_session), _: str = Depends(verify_admin_token)):
    from app.services.analytics import channel_report
    end = end_date or (date.today() - timedelta(days=1))
    start = start_date or (end - timedelta(days=27))
    if start > end or end > date.today() or (end - start).days > 365:
        raise HTTPException(400, "Choose a valid date range of up to 366 days ending today or earlier.")
    channel = session.get(Channel, channel_id)
    if not channel:
        raise HTTPException(404, "Channel not found")
    if not channel.is_connected:
        raise HTTPException(400, "Choose a connected channel")
    if channel.platform == "instagram":
        if (end - start).days > 29 or start < date.today() - timedelta(days=89):
            raise HTTPException(400, "Instagram reports support up to 30 days within the last 90 days.")
        from app.services import meta
        result = meta.insights(channel, start, end)
    elif channel.platform == "youtube":
        result = channel_report(channel, start, end)
        result["platform"] = "youtube"
    else:
        raise HTTPException(400, "Unsupported analytics platform")
    session.add(channel)
    session.commit()
    return result


@router.get("/public/channels")
def list_public_channels(session: Session = Depends(get_session), user: TeamUser = Depends(require_user)):
    """Authenticated team destination list; provider IDs/tokens remain private."""
    channels = session.exec(select(Channel).where(Channel.is_connected == True)).all()  # noqa: E712
    return [{"id": c.id, "platform": c.platform, "display_name": c.display_name} for c in channels]


@router.get("/admin/channels")
def list_admin_channels(session: Session = Depends(get_session), _: str = Depends(verify_admin_token)):
    channels = session.exec(select(Channel)).all()
    return [
        {
            "id": c.id,
            "platform": c.platform,
            "display_name": c.display_name,
            "external_id": c.external_id,
            "is_connected": c.is_connected,
        }
        for c in channels
    ]


@router.get("/admin/channels/{channel_id}/stats")
def channel_stats(channel_id: int, session: Session = Depends(get_session), _: str = Depends(verify_admin_token)):
    from app.services import youtube as yt_service
    channel = session.get(Channel, channel_id)
    if not channel or not channel.is_connected:
        return {"error": "channel not connected"}
    if channel.platform == "youtube":
        result = yt_service.get_channel_stats(channel)
        channel.authorized_at = datetime.utcnow()
        session.add(channel)
        session.commit()
        return result
    return {"error": "analytics not yet wired up for this platform"}


@router.delete("/admin/channels/{channel_id}")
def disconnect(channel_id: int, session: Session = Depends(get_session), _: str = Depends(verify_admin_token)):
    channel = session.get(Channel, channel_id)
    if not channel:
        raise HTTPException(404, "Channel not found")
    was_connected = channel.is_connected
    channel.is_connected = False
    session.add(channel)
    session.commit()
    videos = session.exec(select(Video).where(Video.channel_id == channel_id)).all()
    if any(v.status in ("publishing", "processing") for v in videos):
        channel.is_connected = was_connected
        session.add(channel)
        session.commit()
        raise HTTPException(409, "Finish or recover active publishes before disconnecting")
    if channel.access_token:
        try:
            if channel.platform == "youtube":
                response = httpx.post("https://oauth2.googleapis.com/revoke", data={"token": unseal(channel.refresh_token or channel.access_token)}, timeout=30)
            else:
                from app.services.meta import graph
                graph("DELETE", f"{channel.external_id}/permissions", unseal(channel.access_token))
                response = None
            if response is not None and response.status_code not in (200, 400):
                raise ValueError()
        except Exception:
            # Local deletion must remain available even if the provider is unavailable.
            pass
    channel.is_connected = False
    channel.access_token = None
    channel.refresh_token = None
    session.add(channel)
    session.commit()
    for video in videos:
        storage.delete(video.file_path)
        session.delete(video)
    session.delete(channel)
    session.commit()
    return {"status": "deleted", "message": "App connection and submissions deleted. Also check the provider's connected-app settings to revoke access. Published posts are unchanged."}
