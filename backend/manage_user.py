"""Create/update a team login without putting plaintext passwords in SQL or shell history."""
import argparse
from getpass import getpass
from sqlmodel import Session, select
from app.database import init_db, engine
from app.models import TeamUser, AdminUser
from app.config import settings
from app.security import hash_password
from app.models import Video
from app.services import storage

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("--name")
    parser.add_argument("--admin", action="store_true", help="Manage a database-backed admin instead of a team member")
    parser.add_argument("--disable", action="store_true")
    parser.add_argument("--delete", action="store_true", help="Delete account and submissions, not platform posts")
    args = parser.parse_args()
    init_db()
    with Session(engine) as session:
        username = args.username.strip().lower()
        if not username or len(username) > 100:
            raise SystemExit("Username must contain 1 to 100 characters")
        if args.admin and username == settings.admin_username.strip().lower():
            raise SystemExit("Choose a username different from the existing .env admin account")
        model = AdminUser if args.admin else TeamUser
        user = session.exec(select(model).where(model.username == username)).first()
        if args.delete:
            if not user:
                raise SystemExit("User not found")
            videos = [] if args.admin else session.exec(select(Video).where(Video.uploader_id == user.id)).all()
            if any(v.status in ("publishing", "processing") for v in videos):
                raise SystemExit("Finish or recover active publishes first")
            for video in videos:
                storage.delete(video.file_path)
                session.delete(video)
            session.delete(user)
            session.commit()
            raise SystemExit("Account and app submissions deleted.")
        elif args.disable:
            if not user:
                raise SystemExit("User not found")
            user.is_active = False
        else:
            password = getpass("Password (12+ characters): ")
            if not 12 <= len(password) <= 256 or password != getpass("Confirm password: "):
                raise SystemExit("Passwords must match and contain 12 to 256 characters")
            if not user:
                user = model(username=username, display_name=args.name or username, password_hash="")
            user.password_hash = hash_password(password)
            user.display_name = args.name or user.display_name
            user.is_active = True
        session.add(user)
        session.commit()
    print("Admin account saved." if args.admin else "Team account saved.")
