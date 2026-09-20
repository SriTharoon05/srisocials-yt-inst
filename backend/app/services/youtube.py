"""
YouTube Data API v3 integration.

Implementation notes:
- youtube.upload and youtube.readonly cover upload plus destination identity/stats.
- Each of the 5 channels is authorized individually and its own refresh token is
  stored against that Channel row — we never reuse one channel's token for another.
- Uploads are always set with a safe default privacyStatus ("private") until an
  admin explicitly reviews and publishes — nothing goes live without human review,
  matching what you described (upload -> admin review -> publish).
- Raw OAuth tokens never reach the frontend. Retention is handled separately.
"""
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_httplib2 import AuthorizedHttp
import httplib2

from app.config import settings, YOUTUBE_SCOPES
from app.models import Channel
from app.crypto import seal, unseal

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"


def client(creds):
    return build("youtube", "v3", http=AuthorizedHttp(creds, http=httplib2.Http(timeout=60)))


def build_flow(state: str | None = None) -> Flow:
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": GOOGLE_AUTH_URL,
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=YOUTUBE_SCOPES, state=state)
    flow.redirect_uri = settings.google_redirect_uri
    return flow


def credentials_from_channel(channel: Channel) -> Credentials:
    creds = Credentials(
        token=unseal(channel.access_token),
        refresh_token=unseal(channel.refresh_token),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=channel.scopes.replace(",", " ").split() if channel.scopes else YOUTUBE_SCOPES[:2],
    )
    if channel.token_expiry:
        creds.expiry = channel.token_expiry
    return creds


def refresh_if_needed(channel: Channel) -> Credentials:
    creds = credentials_from_channel(channel)
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        channel.access_token = seal(creds.token)
        channel.token_expiry = creds.expiry
    return creds


def fetch_channel_identity(creds: Credentials) -> dict:
    """Used right after OAuth to confirm *which* channel was just authorized,
    so the admin picks the correct one out of the 5 when connecting."""
    yt = client(creds)
    resp = yt.channels().list(part="snippet,contentDetails", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        return {}
    item = items[0]
    return {
        "external_id": item["id"],
        "title": item["snippet"]["title"],
        "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
    }


def upload_video(channel: Channel, file_path: str, title: str, description: str,
                  privacy_status: str = "private", made_for_kids: bool = False) -> dict:
    """Uploads a reviewed video to the given channel's YouTube account.
    Always uses the channel's own stored credentials — this is what makes the
    'each Publish button uploads to the correct channel' requirement safe."""
    creds = refresh_if_needed(channel)
    if privacy_status not in ("private", "unlisted", "public"):
        raise ValueError("Invalid YouTube visibility")
    identity = fetch_channel_identity(creds)
    if identity.get("external_id") != channel.external_id:
        raise ValueError("Authorized YouTube channel does not match the destination; reconnect")
    channel.authorized_at = datetime.utcnow()
    yt = client(creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "categoryId": "22",  # People & Blogs; adjust per genre if needed
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }
    media = MediaFileUpload(file_path, chunksize=1024 * 1024, resumable=True, mimetype="video/mp4")
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status_, response = request.next_chunk()

    video_id = response["id"]
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "privacy_status": response.get("status", {}).get("privacyStatus", privacy_status),
    }


def get_channel_stats(channel: Channel) -> dict:
    creds = refresh_if_needed(channel)
    yt = client(creds)
    resp = yt.channels().list(part="statistics", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        return {}
    return items[0]["statistics"]
