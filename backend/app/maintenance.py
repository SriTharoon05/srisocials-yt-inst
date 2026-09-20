import logging
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.database import engine
from app.models import Channel, Video, OAuthAttempt
from app.services import storage


def cleanup():
    """Run on startup and hourly while awake; no keep-alive or paid worker required."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    with Session(engine) as session:
        for video in session.exec(select(Video).where(Video.created_at < cutoff)).all():
            if video.status == "publishing" and video.publish_started_at and video.publish_started_at > datetime.utcnow() - timedelta(minutes=15):
                continue
            try:
                storage.delete(video.file_path)
                session.delete(video)
                session.commit()
            except Exception:
                session.rollback()
                logging.warning("Retention cleanup needs retry for video %s", video.id)
        for channel in session.exec(select(Channel)).all():
            if (channel.authorized_at or channel.created_at) < cutoff:
                videos = session.exec(select(Video).where(Video.channel_id == channel.id)).all()
                if any(v.status == "publishing" and v.publish_started_at and v.publish_started_at > datetime.utcnow() - timedelta(minutes=15) for v in videos):
                    continue
                try:
                    for video in videos:
                        storage.delete(video.file_path)
                        session.delete(video)
                    session.delete(channel)
                    session.commit()
                except Exception:
                    session.rollback()
                    logging.warning("Connection cleanup needs retry for channel %s", channel.id)
        for attempt in session.exec(select(OAuthAttempt).where(OAuthAttempt.created_at < datetime.utcnow() - timedelta(minutes=10))).all():
            session.delete(attempt)
        session.commit()
