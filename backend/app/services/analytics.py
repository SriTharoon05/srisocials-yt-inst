"""Read-only YouTube Analytics reports; no cached or fabricated metrics."""
from datetime import date, datetime
from fastapi import HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google_auth_httplib2 import AuthorizedHttp
import httplib2
from app.services import youtube

SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"
METRICS = "views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost"


def rows(report):
    names = [column["name"] for column in report.get("columnHeaders", [])]
    return [dict(zip(names, row)) for row in report.get("rows", [])]


def channel_report(channel, start: date, end: date):
    if SCOPE not in (channel.scopes or "").replace(",", " ").split():
        raise HTTPException(403, "Reconnect this YouTube channel in Channels and allow read-only YouTube Analytics access.")
    try:
        creds = youtube.refresh_if_needed(channel)
        identity = youtube.fetch_channel_identity(creds)
        if identity.get("external_id") != channel.external_id:
            raise HTTPException(409, "The authorized channel does not match this destination. Reconnect it in Channels.")
        api = build("youtubeAnalytics", "v2", http=AuthorizedHttp(creds, http=httplib2.Http(timeout=30)))
        common = {"ids": f"channel=={channel.external_id}", "startDate": start.isoformat(), "endDate": end.isoformat()}
        summary = rows(api.reports().query(**common, metrics=METRICS).execute())
        daily = rows(api.reports().query(**common, metrics="views,estimatedMinutesWatched", dimensions="day", sort="day").execute())
        top = rows(api.reports().query(**common, metrics="views,estimatedMinutesWatched,averageViewDuration",
                                      dimensions="video", sort="-views", maxResults=10).execute())
        # Titles are optional; a metadata lookup failure must not discard analytics.
        if top:
            try:
                videos = youtube.client(creds).videos().list(part="snippet", id=",".join(str(v["video"]) for v in top)).execute()
                titles = {v["id"]: v["snippet"]["title"] for v in videos.get("items", [])}
                for item in top:
                    item["title"] = titles.get(item["video"], item["video"])
            except Exception:
                pass
        channel.authorized_at = datetime.utcnow()
        return {"channel": {"id":channel.id,"name":channel.display_name}, "start_date": start.isoformat(),
                "end_date": end.isoformat(), "summary": summary[0] if summary else None,
                "daily": daily, "top_videos": top, "last_reported_day": daily[-1]["day"] if daily else None}
    except HttpError as exc:
        if exc.resp.status in (401, 403):
            raise HTTPException(403, "YouTube Analytics access was denied. Enable YouTube Analytics API in Google Cloud, then reconnect this channel and grant its analytics permission.") from None
        raise HTTPException(502, "YouTube Analytics could not return this report. Try a different date range or try again shortly.") from None
    except RefreshError:
        raise HTTPException(403, "Google authorization expired. Reconnect this channel in Channels.") from None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Could not reach YouTube Analytics. Try again shortly.") from None
