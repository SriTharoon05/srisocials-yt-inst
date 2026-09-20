"""Create/upgrade only srisocials tables using DATABASE_URL from backend/.env.

Run: python migrate_supabase.py
Existing unrelated tables are never renamed, copied, altered or dropped.
"""
from sqlalchemy import inspect, text
from app.database import engine, init_db
from app.models import Channel, Video, TeamUser, OAuthAttempt, AdminUser

TABLES = tuple(model.__tablename__ for model in (Channel, Video, TeamUser, OAuthAttempt, AdminUser))


def migrate():
    if engine.dialect.name != "postgresql":
        raise SystemExit("Not migrated: DATABASE_URL must be the Supabase Postgres connection string, not SQLite. See deployment.md.")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        init_db()
        with engine.connect() as connection:
            inspector = inspect(connection)
            for name in TABLES:
                if not inspector.has_table(name):
                    raise RuntimeError("Missing application table")
                enabled = connection.execute(text(
                    "SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass(:name)"
                ), {"name": name}).scalar_one()
                if not enabled:
                    raise RuntimeError("Application RLS is not enabled")
            for name in TABLES:
                count = connection.execute(text(f'SELECT count(*) FROM "{name}"')).scalar_one()
                print(f"{name}: ready, RLS enabled, {count} rows")
        print("Supabase schema migration verified. Other projects' tables were not modified.")
    except Exception as exc:
        # Driver errors can contain connection details; keep credentials out of logs.
        raise SystemExit(f"Migration could not be verified ({type(exc).__name__}). Check DATABASE_URL, network access and database permissions. Re-running is safe.") from None


if __name__ == "__main__":
    migrate()
