import uuid
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
                  description: str = Form("", max_length=5000), channel_id: int = Form(...),
                  file: UploadFile = File(...), session: Session = Depends(get_session),
                  user: TeamUser = Depends(require_user)):
    channel = session.get(Channel, channel_id)
    if not channel or not channel.is_connected:
        raise HTTPException(400, "Selected channel is not available")
    if not title.strip() or not genre.strip():
        raise HTTPException(400, "Title and genre are required")
    if channel.platform == "youtube" and (len(description.encode("utf-8")) > 5000 or any(c in title + description for c in "<>")):
        raise HTTPException(400, "YouTube descriptions must fit 5,000 UTF-8 bytes; title/description cannot contain < or >")
    if not (file.filename or "").lower().endswith(".mp4"):
        raise HTTPException(400, "Upload an MP4 video (H.264 video / AAC audio recommended)")
    if channel.platform == "instagram" and len(title) + len(description) + 2 > 2200:
        raise HTTPException(400, "Instagram title plus description must fit within 2,200 characters")
    if file.size and file.size > MAX_BYTES:
        raise HTTPException(413, "Video exceeds the 50 MB limit")
    dest = settings.upload_path / f"{uuid.uuid4().hex}.mp4"
    stored = None
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
        stored = storage.save(dest)
        video = Video(uploader_name=user.display_name, uploader_id=user.id, genre=genre,
                      title=title.strip(), description=description, channel_id=channel_id, file_path=stored)
        session.add(video)
        session.commit()
        session.refresh(video)
        return {"id": video.id, "status": video.status}
    except Exception:
        session.rollback()
        if stored:
            storage.delete(stored)
        raise
    finally:
        if not stored or stored.startswith("supabase:"):
            dest.unlink(missing_ok=True)
        file.file.close()


@router.get("/uploads/mine")
def my_uploads(session: Session = Depends(get_session), user: TeamUser = Depends(require_user)):
    videos = session.exec(select(Video).where(Video.uploader_id == user.id).order_by(Video.created_at.desc())).all()
    return [{"id": v.id, "title": v.title, "genre": v.genre, "status": v.status,
             "created_at": v.created_at} for v in videos]
