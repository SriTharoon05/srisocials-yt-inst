import secrets
from datetime import datetime, timedelta
from typing import Literal
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from itsdangerous import URLSafeTimedSerializer, BadSignature
from sqlalchemy import update
from sqlmodel import Session, select
from app.database import get_session
from app.models import Video, Channel, AdminUser
from app.security import create_admin_token, verify_admin_token, check_password, hash_password
from app.config import settings
from app.services import youtube as yt_service, meta, storage

router = APIRouter(prefix="/admin", tags=["admin"])
DUMMY_ADMIN_HASH = hash_password("not-a-real-admin-password")


class LoginBody(BaseModel):
    username: str = Field(max_length=100)
    password: str = Field(max_length=256)


@router.post("/login")
def login(body: LoginBody, session: Session = Depends(get_session)):
    user = session.exec(select(AdminUser).where(AdminUser.username == body.username.strip().lower())).first()
    valid = check_password(body.password, user.password_hash if user else DUMMY_ADMIN_HASH)
    if user:
        if not user.is_active or not valid:
            raise HTTPException(401, "Invalid credentials")
        return {"token": create_admin_token(user)}
    if not (secrets.compare_digest(body.username.encode(), settings.admin_username.encode()) and
            secrets.compare_digest(body.password.encode(), settings.admin_password.encode())):
        raise HTTPException(401, "Invalid credentials")
    return {"token": create_admin_token()}


@router.get("/videos")
def list_videos(status: str | None = None, session: Session = Depends(get_session), _: str = Depends(verify_admin_token)):
    query = select(Video)
    if status:
        query = query.where(Video.status == status)
    result = []
    for v in session.exec(query.order_by(Video.created_at.desc())).all():
        channel = session.get(Channel, v.channel_id)
        result.append({"id": v.id, "uploader_name": v.uploader_name, "genre": v.genre,
            "title": v.title, "description": v.description, "status": v.status,
            "channel": {"id": channel.id, "display_name": channel.display_name, "platform": channel.platform} if channel else None,
            "published_url": v.published_url, "created_at": v.created_at, "made_for_kids": v.made_for_kids,
            "publish_error": v.publish_error, "privacy_status": v.privacy_status})
    return result


def preview_serializer():
    return URLSafeTimedSerializer(settings.admin_session_secret, salt="video-preview")


@router.get("/videos/{video_id}/preview-url")
def preview_url(video_id: int, session: Session = Depends(get_session), _: str = Depends(verify_admin_token)):
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Not found")
    if video.file_path.startswith("supabase:"):
        return {"url": storage.signed_url(video.file_path, 900)}
    token = preview_serializer().dumps({"video_id": video_id})
    return {"url": f"{settings.public_backend_url}/admin/videos/{video_id}/preview?token={token}"}


@router.get("/videos/{video_id}/preview")
def preview_video(video_id: int, token: str, session: Session = Depends(get_session)):
    try:
        if preview_serializer().loads(token, max_age=900)["video_id"] != video_id:
            raise ValueError()
    except (BadSignature, ValueError, KeyError):
        raise HTTPException(401, "Preview expired; reload the queue")
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Not found")
    if video.file_path.startswith("supabase:"):
        return RedirectResponse(storage.signed_url(video.file_path, 900))
    if not Path(video.file_path).is_file():
        raise HTTPException(404, "Video file is missing")
    return FileResponse(video.file_path, media_type="video/mp4")


class ReviewBody(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
    made_for_kids: bool | None = None


def review(video_id, body, status, session):
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Not found")
    channel = session.get(Channel, video.channel_id)
    if status == "approved" and channel and channel.platform == "youtube" and body.made_for_kids is None:
        raise HTTPException(400, "Choose whether this YouTube video is made for kids")
    result = session.exec(update(Video).where(Video.id == video_id, Video.status == "pending").values(
        status=status, review_notes=body.notes, made_for_kids=body.made_for_kids, reviewed_at=datetime.utcnow()))
    session.commit()
    if result.rowcount != 1:
        raise HTTPException(409, "Only pending videos can be reviewed")
    return {"status": status}


@router.post("/videos/{video_id}/approve")
def approve(video_id: int, body: ReviewBody, session: Session = Depends(get_session), _: str = Depends(verify_admin_token)):
    return review(video_id, body, "approved", session)


@router.post("/videos/{video_id}/reject")
def reject(video_id: int, body: ReviewBody, session: Session = Depends(get_session), _: str = Depends(verify_admin_token)):
    return review(video_id, body, "rejected", session)


class PublishBody(BaseModel):
    privacy_status: Literal["private", "unlisted", "public"] = "private"


@router.post("/videos/{video_id}/publish")
def publish(video_id: int, body: PublishBody, session: Session = Depends(get_session), _: str = Depends(verify_admin_token)):
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Not found")
    if video.status == "published":
        return {"status": "published", "url": video.published_url}
    channel = session.get(Channel, video.channel_id)
    if not channel or not channel.is_connected:
        raise HTTPException(400, "Destination channel is not connected")
    if channel.platform not in ("youtube", "instagram"):
        raise HTTPException(400, "Unsupported destination")
    if channel.platform == "youtube" and video.made_for_kids is None:
        raise HTTPException(400, "Audience selection is required; review this submission again")
    claim = session.exec(update(Video).where(Video.id == video_id, Video.status.in_(["approved", "processing"]),
        Video.channel_id.in_(select(Channel.id).where(Channel.is_connected == True)))
        .values(status="publishing", publish_started_at=datetime.utcnow(), publish_error=None))
    session.commit()
    if claim.rowcount != 1:
        raise HTTPException(409, "Already publishing or not approved. Refresh the queue.")
    session.refresh(video)
    external_publish_started = False
    try:
        if channel.platform == "youtube":
            with storage.local_file(video.file_path) as path:
                external_publish_started = True
                result = yt_service.upload_video(channel, path, video.title, video.description or "", body.privacy_status, video.made_for_kids)
            video.youtube_video_id = result["video_id"]
            video.platform_media_id = result["video_id"]
            video.published_url = result["url"]
            video.privacy_status = result.get("privacy_status", body.privacy_status)
        else:
            token = meta.refresh(channel)
            session.add(channel)
            session.commit()
            if not video.meta_container_id:
                url = storage.signed_url(video.file_path, 3600)
                video.meta_container_id = meta.create_container(channel, token, video, url)
                session.add(video)
                session.commit()
            state = meta.container_status(video.meta_container_id, token)
            if state in ("IN_PROGRESS", "IN_PROCESS"):
                video.status = "processing"
                session.add(video)
                session.commit()
                return {"status": "processing", "message": "Instagram is processing the Reel. Check again shortly."}
            if state in ("ERROR", "EXPIRED"):
                video.meta_container_id = None
                session.add(video)
                session.commit()
                raise HTTPException(400, "Instagram rejected or expired this media container; verify Reel format before retrying")
            if state != "FINISHED":
                external_publish_started = True
                raise HTTPException(409, "Check Instagram before retrying: container may already be published")
            external_publish_started = True
            video.platform_media_id = meta.publish_container(channel, video.meta_container_id, token)
            video.privacy_status = "public"
            # Save the provider ID before the optional permalink lookup.
            video.status = "published"
            video.published_at = datetime.utcnow()
            session.add(video)
            session.commit()
            try:
                video.published_url = meta.permalink(video.platform_media_id, token)
            except Exception:
                pass
        video.status = "published"
        video.published_at = datetime.utcnow()
        session.add(channel)
        session.add(video)
        session.commit()
        return {"status": "published", "url": video.published_url}
    except Exception as exc:
        session.rollback()
        session.refresh(video)
        if video.status == "published":
            return {"status": "published", "url": video.published_url}
        if isinstance(exc, yt_service.UploadNotStarted):
            external_publish_started = False
        video.status = "publish_unknown" if external_publish_started else "approved"
        video.publish_error = ("Publish result is uncertain. Check the destination before resetting; do not upload a duplicate."
                               if external_publish_started else (str(exc) if isinstance(exc, yt_service.UploadNotStarted) else str(exc.detail) if isinstance(exc, HTTPException) else "Publishing failed before posting. Check connection, storage and media format, then retry."))
        session.add(video)
        session.commit()
        raise HTTPException(502, video.publish_error) from None


class ResetBody(BaseModel):
    confirmed_not_published: Literal[True]


@router.post("/videos/{video_id}/reset-publish")
def reset_publish(video_id: int, body: ResetBody, session: Session = Depends(get_session), _: str = Depends(verify_admin_token)):
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Not found")
    if video.status == "publishing" and (not video.publish_started_at or video.publish_started_at > datetime.utcnow() - timedelta(minutes=15)):
        raise HTTPException(409, "Wait 15 minutes before recovering an interrupted publish")
    if video.status not in ("publishing", "publish_unknown"):
        raise HTTPException(409, "This submission does not need recovery")
    result = session.exec(update(Video).where(Video.id == video_id, Video.status == video.status,
        Video.publish_started_at == video.publish_started_at).values(status="approved", meta_container_id=None, publish_error=None))
    session.commit()
    if result.rowcount != 1:
        raise HTTPException(409, "Publish state changed; refresh before recovering")
    return {"status": "approved"}


@router.delete("/videos/{video_id}")
def delete_video(video_id: int, session: Session = Depends(get_session), _: str = Depends(verify_admin_token)):
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Not found")
    claim = session.exec(update(Video).where(Video.id == video_id, Video.status.notin_(["publishing", "processing", "deleting"]))
                         .values(status="deleting"))
    session.commit()
    if claim.rowcount != 1:
        raise HTTPException(409, "Cannot delete while publishing or processing")
    try:
        storage.delete(video.file_path)
    except Exception:
        video.status = "rejected"
        session.add(video)
        session.commit()
        raise
    session.delete(video)
    session.commit()
    return {"status": "deleted", "message": "App copy deleted. Platform post is unchanged."}
