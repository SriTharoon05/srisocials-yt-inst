"""
Optional helper: pre-create 5 placeholder Instagram channel rows so they show
up in the admin dashboard before you wire up Meta OAuth. YouTube channels don't
need this — they get created automatically the first time you connect one via
/auth/google/login.

Run once:  python seed_channels.py
"""
from sqlmodel import Session, select
from app.database import engine, init_db
from app.models import Channel

INSTAGRAM_PLACEHOLDERS = [
    "Insta Page 1", "Insta Page 2", "Insta Page 3", "Insta Page 4", "Insta Page 5",
]

if __name__ == "__main__":
    init_db()
    with Session(engine) as session:
        for name in INSTAGRAM_PLACEHOLDERS:
            existing = session.exec(
                select(Channel).where(Channel.platform == "instagram", Channel.display_name == name)
            ).first()
            if not existing:
                session.add(Channel(platform="instagram", display_name=name, is_connected=False))
        session.commit()
    print("Seeded placeholder Instagram channels (not connected yet).")
