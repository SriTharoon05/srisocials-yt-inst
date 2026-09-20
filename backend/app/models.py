from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Channel(SQLModel, table=True):
    """A destination channel/page the team can upload to.

    platform: "youtube" | "instagram"
    external_id: YouTube channel ID or Instagram Business Account ID
    """
    __tablename__ = "srisocials_channel"
    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str
    display_name: str
    external_id: Optional[str] = None

    # OAuth tokens (stored per-channel, since each of your 5 YouTube
    # channels / 5 Instagram pages is authorized separately)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    scopes: Optional[str] = None
    authorized_at: Optional[datetime] = None

    is_connected: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Video(SQLModel, table=True):
    __tablename__ = "srisocials_video"
    id: Optional[int] = Field(default=None, primary_key=True)

    # Display name is captured from the authenticated team account.
    uploader_name: str
    uploader_id: Optional[int] = Field(default=None, foreign_key="srisocials_teamuser.id")
    genre: str
    title: str
    description: Optional[str] = ""

    channel_id: int = Field(foreign_key="srisocials_channel.id")

    file_path: str
    thumbnail_path: Optional[str] = None

    # pending -> approved/rejected -> published
    status: str = Field(default="pending")
    review_notes: Optional[str] = None

    youtube_video_id: Optional[str] = None
    published_url: Optional[str] = None
    made_for_kids: Optional[bool] = None
    meta_container_id: Optional[str] = None
    platform_media_id: Optional[str] = None
    privacy_status: Optional[str] = None
    publish_error: Optional[str] = None
    publish_started_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    published_at: Optional[datetime] = None


class TeamUser(SQLModel, table=True):
    __tablename__ = "srisocials_teamuser"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    display_name: str
    password_hash: str
    is_active: bool = True


class OAuthAttempt(SQLModel, table=True):
    __tablename__ = "srisocials_oauthattempt"
    state: str = Field(primary_key=True)
    provider: str
    browser_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AdminUser(SQLModel, table=True):
    __tablename__ = "srisocials_adminuser"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    display_name: str
    password_hash: str
    is_active: bool = True
