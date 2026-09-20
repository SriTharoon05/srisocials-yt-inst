from unittest.mock import Mock
from datetime import date, timedelta
from pathlib import Path
from sqlmodel import Session
from test_workflow import setup, MP4, upload, approve
from app.models import Channel, Video
from app.services import youtube, meta, storage
from app.config import settings


def test_two_destinations_and_independent_deletion(setup):
    client, engine, admin, team = setup
    with Session(engine) as s:
        s.add(Channel(platform="instagram", display_name="IG", is_connected=True))
        s.commit()
    body = {"title":"Both", "genre":"Other", "youtube_channel_id":1, "instagram_channel_id":2}
    result = client.post("/public/uploads", headers=team, data=body, files={"file":("test.mp4",MP4,"video/mp4")})
    assert result.status_code == 200
    ids = [v["id"] for v in result.json()["submissions"]]
    with Session(engine) as s:
        paths = [s.get(Video, i).file_path for i in ids]
    assert len(set(paths)) == 2
    assert client.delete(f"/admin/videos/{ids[0]}", headers=admin).status_code == 200
    assert Path(paths[1]).read_bytes() == MP4
    mine = client.get("/public/uploads/mine", headers=team).json()
    assert mine[0]["channel"]["platform"] == "instagram"


def test_destinations_validate_before_saving(setup, monkeypatch):
    client, engine, admin, team = setup
    save = Mock()
    monkeypatch.setattr(storage,"save",save)
    for fields in ({}, {"instagram_channel_id":1}, {"youtube_channel_id":1,"instagram_channel_id":999}):
        r=client.post("/public/uploads",headers=team,data={"title":"x","genre":"x",**fields},files={"file":("x.mp4",MP4,"video/mp4")})
        assert r.status_code == 400
    save.assert_not_called()


def test_known_preflight_failure_stays_approved(setup, monkeypatch):
    client, engine, admin, team = setup
    vid=upload(client,team).json()["id"]
    approve(client,admin,vid)
    monkeypatch.setattr(youtube,"upload_video",Mock(side_effect=youtube.UploadNotStarted("Reconnect this channel")))
    r=client.post(f"/admin/videos/{vid}/publish",headers=admin,json={})
    assert r.status_code == 502 and "Reconnect" in r.text
    with Session(engine) as s:
        assert s.get(Video,vid).status == "approved"


def test_instagram_insights_totals_not_summed(monkeypatch):
    monkeypatch.setattr(meta,"refresh",lambda c:"token")
    graph=Mock(side_effect=[{"data":[{"name":"reach","total_value":{"value":7}}]}, {"data":[{"values":[{"value":5,"end_time":"2026-09-18T00:00:00+0000"},{"value":6,"end_time":"2026-09-19T00:00:00+0000"}]}]}])
    monkeypatch.setattr(meta,"graph",graph)
    r=meta.insights(Channel(id=1,platform="instagram",display_name="IG",external_id="ig"),date(2026,9,17),date(2026,9,18))
    assert r["summary"]["reach"] == 7
    assert [v["reach"] for v in r["daily"]] == [5,6]
    assert graph.call_args_list[0].kwargs["metric_type"] == "total_value"


def test_instagram_report_range_and_role(setup,monkeypatch):
    client,engine,admin,team=setup
    with Session(engine) as s:
        c=s.get(Channel,1);c.platform="instagram";s.add(c);s.commit()
    report=Mock(return_value={"platform":"instagram"})
    monkeypatch.setattr(meta,"insights",report)
    assert client.get("/admin/channels/1/analytics",headers=team).status_code==401
    end=date.today()-timedelta(days=1)
    assert client.get(f"/admin/channels/1/analytics?start_date={end-timedelta(days=31)}&end_date={end}",headers=admin).status_code==400
    report.assert_not_called()
    assert client.get("/admin/channels/1/analytics",headers=admin).status_code==200


def test_oauth_start_uses_provider_callback_host(setup,monkeypatch):
    client,engine,admin,team=setup
    monkeypatch.setattr(settings,"meta_app_id","id")
    monkeypatch.setattr(settings,"meta_app_secret","secret")
    monkeypatch.setattr(settings,"meta_redirect_uri","https://example.onrender.com/auth/meta/callback")
    r=client.get("/auth/meta/login",headers=admin)
    assert r.json()["authorization_url"].startswith("https://example.onrender.com/auth/meta/start?")


def test_partial_storage_failure_removes_first_copy(setup,monkeypatch):
    client,engine,admin,team=setup
    with Session(engine) as s:
        s.add(Channel(platform="instagram",display_name="IG",is_connected=True));s.commit()
    save=Mock(side_effect=["supabase:first", RuntimeError("storage offline")])
    delete=Mock()
    monkeypatch.setattr(storage,"save",save)
    monkeypatch.setattr(storage,"delete",delete)
    import pytest
    with pytest.raises(RuntimeError):
        client.post("/public/uploads",headers=team,data={"title":"x","genre":"x","youtube_channel_id":1,"instagram_channel_id":2},files={"file":("x.mp4",MP4,"video/mp4")})
    delete.assert_called_once_with("supabase:first")
    assert client.get("/public/uploads/mine",headers=team).json()==[]


def test_decryption_error_never_attempts_youtube_upload(monkeypatch):
    import pytest
    check=Mock(side_effect=RuntimeError("Cannot decrypt channel credentials"))
    api=Mock()
    monkeypatch.setattr(youtube,"refresh_if_needed",check)
    monkeypatch.setattr(youtube,"client",api)
    with pytest.raises(youtube.UploadNotStarted):
        youtube.upload_video(Channel(platform="youtube",display_name="Old key"),"unused.mp4","title","")
    api.assert_not_called()
