import uuid
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import Video, Channel, TeamUser
from app.config import settings
from app.security import require_user
from app.services import storage

router = APIRouter(prefix="/public", tags=["uploads"])
MAX_BYTES = 50 * 1024 * 1024


@router.post("/uploads")
def create_upload(genre: str = Form(..., max_length=100), title: str = Form(..., max_length=100),
                  description: str = Form("", max_length=5000), channel_id: int | None = Form(None),
                  youtube_channel_id: int | None = Form(None), instagram_channel_id: int | None = Form(None),
                  file: UploadFile = File(...), session: Session = Depends(get_session),
                  user: TeamUser = Depends(require_user)):
    selections = [(channel_id, None), (youtube_channel_id, "youtube"), (instagram_channel_id, "instagram")]
    if channel_id is not None and (youtube_channel_id is not None or instagram_channel_id is not None):
        raise HTTPException(400, "Use either a single destination or the two platform selectors")
    channels = []
    for selected, platform in selections:
        if selected is None:
            continue
        channel = session.get(Channel, selected)
        if not channel or not channel.is_connected or (platform and channel.platform != platform):
            raise HTTPException(400, "Selected channel is not available for this platform")
        channels.append(channel)
    if not channels:
        raise HTTPException(400, "Select at least one YouTube or Instagram destination")
    if not title.strip() or not genre.strip():
        raise HTTPException(400, "Title and genre are required")
    for channel in channels:
        if channel.platform == "youtube" and (len(description.encode("utf-8")) > 5000 or any(c in title + description for c in "<>")):
            raise HTTPException(400, "YouTube descriptions must fit 5,000 UTF-8 bytes; title/description cannot contain < or >")
        if channel.platform == "instagram" and len(title.strip()) + len(description) + 2 > 2200:
            raise HTTPException(400, "Instagram title plus description must fit within 2,200 characters")
    if not (file.filename or "").lower().endswith(".mp4"):
        raise HTTPException(400, "Upload an MP4 video (H.264 video / AAC audio recommended)")
    if file.size and file.size > MAX_BYTES:
        raise HTTPException(413, "Video exceeds the 50 MB limit")
    dest = settings.upload_path / f"{uuid.uuid4().hex}.mp4"
    stored_paths = []
    temporary_paths = [dest]
    try:
        total = 0
        with dest.open("wb") as out:
            while chunk := file.file.read(1024 * 1024):
                if total == 0 and (len(chunk) < 12 or chunk[4:8] != b"ftyp"):
                    raise HTTPException(400, "File is not an MP4 container")
                total += len(chunk)
                if total > MAX_BYTES:
                    raise HTTPException(413, "Video exceeds the 50 MB limit")
                out.write(chunk)
        if total == 0:
            raise HTTPException(400, "Video is empty")
        videos = []
        for channel in channels:
            # Separate objects let either destination be deleted or retained independently.
            copy = settings.upload_path / f"{uuid.uuid4().hex}.mp4"
            temporary_paths.append(copy)
            shutil.copyfile(dest, copy)
            stored = storage.save(copy)
            stored_paths.append(stored)
            video = Video(uploader_name=user.display_name, uploader_id=user.id, genre=genre,
                          title=title.strip(), description=description, channel_id=channel.id, file_path=stored)
            session.add(video)
            videos.append(video)
        session.flush()
        result = {"submissions": [{"id": v.id, "status": v.status, "channel_id": v.channel_id} for v in videos]}
        if len(videos) == 1:
            result.update(id=videos[0].id, status=videos[0].status)
        session.commit()
        return result
    except Exception:
        session.rollback()
        for stored in stored_paths:
            storage.delete(stored)
        raise
    finally:
        for path in temporary_paths:
            if str(path) not in stored_paths:
                path.unlink(missing_ok=True)
        file.file.close()


@router.get("/uploads/mine")
def my_uploads(session: Session = Depends(get_session), user: TeamUser = Depends(require_user)):
    videos = session.exec(select(Video).where(Video.uploader_id == user.id).order_by(Video.created_at.desc())).all()
    return [{"id": v.id, "title": v.title, "genre": v.genre, "status": v.status,
             "created_at": v.created_at, "channel": {"platform": c.platform, "display_name": c.display_name} if (c := session.get(Channel, v.channel_id)) else None} for v in videos]
