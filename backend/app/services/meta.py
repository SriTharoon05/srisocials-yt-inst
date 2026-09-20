"""Instagram API with Instagram Login (professional accounts, no Facebook Page)."""
from datetime import datetime, timedelta
from urllib.parse import urlencode
import httpx
from fastapi import HTTPException
from app.config import settings
from app.crypto import seal, unseal

SCOPES = "instagram_business_basic,instagram_business_content_publish,instagram_business_manage_insights"


def decode(response):
    try:
        data = response.json()
    except ValueError:
        raise HTTPException(502, "Instagram returned an invalid response")
    if response.is_error or "error" in data:
        # Do not expose provider responses (they can contain tokens or signed URLs).
        code = data.get("error", {}).get("code", "unknown") if isinstance(data.get("error"), dict) else "unknown"
        if code in (10, 190, 200):
            raise HTTPException(403, f"Instagram access was denied or expired (code {code}). Reconnect this account with the required permissions; Insights requires instagram_business_manage_insights.")
        raise HTTPException(502, f"Instagram request failed (code {code}); check permissions, media format, or reconnect")
    return data


def authorization_url(state):
    return "https://www.instagram.com/oauth/authorize?" + urlencode({
        "client_id": settings.meta_app_id, "redirect_uri": settings.meta_redirect_uri,
        "response_type": "code", "scope": SCOPES, "state": state,
        "enable_fb_login": "0", "force_authentication": "1"})


def exchange(code):
    short = decode(httpx.post("https://api.instagram.com/oauth/access_token", data={
        "client_id": settings.meta_app_id, "client_secret": settings.meta_app_secret,
        "grant_type": "authorization_code", "redirect_uri": settings.meta_redirect_uri, "code": code}, timeout=30))
    long = decode(httpx.get("https://graph.instagram.com/access_token", params={
        "grant_type": "ig_exchange_token", "client_secret": settings.meta_app_secret,
        "access_token": short["access_token"]}, timeout=30))
    return long


def graph(method, path, token, **params):
    url = f"https://graph.instagram.com/{settings.meta_api_version}/{path}"
    return decode(httpx.request(method, url, headers={"Authorization": f"Bearer {token}"},
        params=params if method == "GET" else None, data=params if method != "GET" else None, timeout=30))


def identity(token):
    return graph("GET", "me", token, fields="user_id,username")


def refresh(channel):
    token = unseal(channel.access_token)
    if not channel.token_expiry or channel.token_expiry <= datetime.utcnow():
        raise HTTPException(400, "Instagram connection expired; reconnect in Channels")
    if channel.token_expiry < datetime.utcnow() + timedelta(days=7):
        result = decode(httpx.get("https://graph.instagram.com/refresh_access_token", params={
            "grant_type": "ig_refresh_token", "access_token": token}, timeout=30))
        token = result["access_token"]
        channel.access_token = seal(token)
        channel.token_expiry = datetime.utcnow() + timedelta(seconds=result["expires_in"])
    account = identity(token)
    if str(account.get("user_id")) != channel.external_id:
        raise HTTPException(400, "Instagram account mismatch; reconnect the destination")
    channel.authorized_at = datetime.utcnow()
    return token


def create_container(channel, token, video, url):
    return graph("POST", f"{channel.external_id}/media", token, media_type="REELS",
                 video_url=url, caption=f"{video.title}\n\n{video.description or ''}".strip(),
                 share_to_feed="true")["id"]


def container_status(container, token):
    return graph("GET", container, token, fields="status_code")["status_code"]


def publish_container(channel, container, token):
    return graph("POST", f"{channel.external_id}/media_publish", token, creation_id=container)["id"]


def permalink(media_id, token):
    return graph("GET", media_id, token, fields="permalink").get("permalink")


def insights(channel, start, end):
    from datetime import time, timezone
    token = refresh(channel)
    since = int(datetime.combine(start, time.min, tzinfo=timezone.utc).timestamp())
    until = int(datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc).timestamp())
    common = dict(period="day", since=since, until=until)
    result = graph("GET", f"{channel.external_id}/insights", token,
                   metric="views,reach,accounts_engaged,total_interactions", metric_type="total_value", **common)
    summary = {item["name"]: item.get("total_value", {}).get("value") for item in result.get("data", [])}
    daily = []
    warnings = []
    try:
        series = graph("GET", f"{channel.external_id}/insights", token, metric="reach", metric_type="time_series", **common)
        for item in series.get("data", []):
            for value in item.get("values", []):
                daily.append({"day": value.get("end_time", "")[:10], "reach": value.get("value")})
    except HTTPException:
        warnings.append("Daily reach is unavailable for this account or date range.")
    return {"platform": "instagram", "channel": {"id": channel.id, "name": channel.display_name},
            "start_date": start.isoformat(), "end_date": end.isoformat(), "summary": summary or None,
            "daily": daily, "warnings": warnings}
