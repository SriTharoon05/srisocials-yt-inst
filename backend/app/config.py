from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_redirect_uri: str = "http://localhost:8000/auth/meta/callback"
    meta_api_version: str = "v25.0"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "videos"  # Override with the existing bucket name in .env.
    token_encryption_key: str = ""
    environment: str = "development"
    public_backend_url: str = "http://localhost:8000"
    privacy_contact_email: str = ""
    operator_name: str = "srisocials administrator"

    admin_username: str = "admin"
    admin_password: str = "change_me"
    admin_session_secret: str = "change_this_to_a_long_random_string"

    frontend_user_origin: str = "http://localhost:5173"
    frontend_admin_origin: str = "http://localhost:5174"

    upload_dir: str = "uploads"
    database_url: str = "sqlite:///./srisocials.db"

    class Config:
        env_file = str(Path(__file__).resolve().parents[1] / ".env")

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
