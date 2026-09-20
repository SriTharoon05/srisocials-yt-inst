from datetime import date
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from app.models import Channel
from app.services import analytics, youtube
from app.crypto import seal
from test_workflow import setup


def report(columns, values):
    return {"columnHeaders": [{"name": c} for c in columns], "rows": values}


def test_analytics_queries_and_titles(monkeypatch):
    channel = Channel(id=7, platform="youtube", display_name="Stories", external_id="yt-7", scopes=analytics.SCOPE)
    monkeypatch.setattr(youtube, "refresh_if_needed", Mock(return_value=Mock()))
    monkeypatch.setattr(youtube, "fetch_channel_identity", Mock(return_value={"external_id": "yt-7"}))
    api = Mock()
    query = api.reports.return_value.query
    query.return_value.execute.side_effect = [
        report(analytics.METRICS.split(","), [[100, 50, 30, 3, 1]]),
        report(["day", "views", "estimatedMinutesWatched"], [["2026-08-01", 100, 50]]),
        report(["video", "views", "estimatedMinutesWatched", "averageViewDuration"], [["v1", 100, 50, 30]])]
    monkeypatch.setattr(analytics, "build", Mock(return_value=api))
    metadata = Mock()
    metadata.videos.return_value.list.return_value.execute.return_value = {"items": [{"id": "v1", "snippet": {"title": "Story"}}]}
    monkeypatch.setattr(youtube, "client", Mock(return_value=metadata))
    result = analytics.channel_report(channel, date(2026, 8, 1), date(2026, 8, 2))
    assert result["summary"]["views"] == 100
    assert result["top_videos"][0]["title"] == "Story"
    assert result["last_reported_day"] == "2026-08-01"
    for call in query.call_args_list:
        assert call.kwargs["ids"] == "channel==yt-7"
        assert call.kwargs["startDate"] == "2026-08-01"
        assert call.kwargs["endDate"] == "2026-08-02"
    assert query.call_args_list[2].kwargs["maxResults"] == 10


def test_analytics_requires_explicit_grant(monkeypatch):
    refresh = Mock()
    monkeypatch.setattr(youtube, "refresh_if_needed", refresh)
    with pytest.raises(HTTPException) as error:
        analytics.channel_report(Channel(platform="youtube", display_name="Old grant"), date.today(), date.today())
    assert error.value.status_code == 403
    refresh.assert_not_called()


def test_analytics_endpoint_authorization_and_date_validation(setup, monkeypatch):
    client, engine, admin, team = setup
    service = Mock(return_value={"summary": None, "daily": [], "top_videos": []})
    monkeypatch.setattr(analytics, "channel_report", service)
    url = "/admin/channels/1/analytics"
    assert client.get(url, headers=team).status_code == 401
    assert client.get(url + "?start_date=2026-08-02&end_date=2026-08-01", headers=admin).status_code == 400
    service.assert_not_called()
    assert client.get(url + "?start_date=2025-08-01&end_date=2025-08-02", headers=admin).status_code == 200
    assert service.call_args.args[1:] == (date(2025, 8, 1), date(2025, 8, 2))


def test_existing_upload_credentials_do_not_expand_scope():
    channel = Channel(platform="youtube", display_name="Legacy", access_token=seal("access"), refresh_token=seal("refresh"))
    assert analytics.SCOPE not in youtube.credentials_from_channel(channel).scopes
