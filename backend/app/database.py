from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
from sqlalchemy import inspect, text

database_url = settings.database_url
if database_url.startswith(("postgres://", "postgresql://")):
    database_url = "postgresql+psycopg://" + database_url.split("://", 1)[1]

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)


def init_db():
    from app import models  # noqa
    app_tables = [models.Channel.__table__, models.Video.__table__,
                  models.TeamUser.__table__, models.OAuthAttempt.__table__, models.AdminUser.__table__]
    SQLModel.metadata.create_all(engine, tables=app_tables)
    # Additive upgrade for the original SQLite/Postgres schema. No data is dropped.
    additions = {
        "srisocials_channel": {"authorized_at": "TIMESTAMP"},
        "srisocials_video": {"uploader_id": "INTEGER", "made_for_kids": "BOOLEAN",
                  "meta_container_id": "VARCHAR", "platform_media_id": "VARCHAR",
                  "publish_error": "VARCHAR", "publish_started_at": "TIMESTAMP", "privacy_status": "VARCHAR"},
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {c["name"] for c in inspect(connection).get_columns(table)}
            for name, kind in columns.items():
                if name not in existing:
                    connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {kind}'))
        if engine.dialect.name == "postgresql":
            # The backend uses its database role. Supabase anon/authenticated REST
            # clients must not be able to read password hashes or OAuth credentials.
            for table in app_tables:
                connection.execute(text(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY'))
        connection.execute(text("UPDATE srisocials_channel SET access_token=NULL, refresh_token=NULL, is_connected=false "
            "WHERE access_token IS NOT NULL AND access_token NOT LIKE 'enc:%'"))


def get_session():
    with Session(engine) as session:
        yield session
