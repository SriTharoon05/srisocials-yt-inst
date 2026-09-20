import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
import pytest
from cryptography.fernet import Fernet

# conftest.py isolates credentials before application imports.

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from app.main import app
from app.config import settings
from app import database, maintenance
from app.models import Channel, Video, TeamUser, OAuthAttempt
from app.security import hash_password
from app.crypto import seal, unseal
from app.services import youtube, meta, storage

MP4 = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 128


@pytest.fixture
def setup(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(maintenance, "engine", engine)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    # No retention thread race against fixtures; retention has its own explicit test.
    monkeypatch.setattr("app.main.cleanup", lambda: None)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(TeamUser(username="alice", display_name="Alice", password_hash=hash_password("password123456")))
        session.add(TeamUser(username="bob", display_name="Bob", password_hash=hash_password("password123456")))
        session.add(Channel(platform="youtube", display_name="Test channel", external_id="yt-1", is_connected=True,
                            access_token=seal("access"), refresh_token=seal("refresh"), authorized_at=datetime.utcnow()))
        session.commit()
    with TestClient(app) as client:
        middleware = app.middleware_stack
        while middleware is not None:
            if hasattr(middleware, "attempts"):
                middleware.attempts.clear()
            middleware = getattr(middleware, "app", None)
        admin = client.post("/admin/login", json={"username": "admin", "password": "test-password-123"}).json()["token"]
        team = client.post("/team/login", json={"username": "alice", "password": "password123456"}).json()["token"]
        yield client, engine, {"Authorization": f"Bearer {admin}"}, {"Authorization": f"Bearer {team}"}
    engine.dispose()


def upload(client, headers, **extra):
    return client.post("/public/uploads", headers=headers, data={"title":"A cut", "genre":"Tech", "channel_id":"1", **extra}, files={"file":("cut.mp4",MP4,"video/mp4")})


def approve(client, headers, video_id):
    return client.post(f"/admin/videos/{video_id}/approve", headers=headers, json={"made_for_kids":False})


def test_end_to_end_private_upload_and_duplicate_click(setup, monkeypatch):
    client, engine, admin, team = setup
    response = upload(client, team, uploader_name="Impersonation")
    assert response.status_code == 200, response.text
    vid = response.json()["id"]
    queue = client.get("/admin/videos?status=pending", headers=admin).json()
    assert queue[0]["uploader_name"] == "Alice"
    url = client.get(f"/admin/videos/{vid}/preview-url", headers=admin).json()["url"]
    preview = client.get(url)
    assert preview.content == MP4
    partial = client.get(url, headers={"Range":"bytes=0-11"})
    assert partial.status_code == 206
    assert client.post(f"/admin/videos/{vid}/publish", headers=admin, json={}).status_code == 400
    assert approve(client, admin, vid).status_code == 200
    mock = Mock(return_value={"video_id":"uploaded", "url":"https://www.youtube.com/watch?v=uploaded"})
    monkeypatch.setattr(youtube,"upload_video",mock)
    assert client.post(f"/admin/videos/{vid}/publish", headers=admin, json={"privacy_status":"invalid"}).status_code == 422
    assert client.post(f"/admin/videos/{vid}/publish", headers=admin, json={}).json()["status"] == "published"
    assert mock.call_args.args[4:] == ("private",False)
    client.post(f"/admin/videos/{vid}/publish", headers=admin, json={})
    assert mock.call_count == 1
    assert approve(client, admin, vid).status_code == 409


def test_authorization_and_ownership(setup):
    client, engine, admin, team = setup
    assert upload(client, {}).status_code == 401
    assert client.get("/public/channels").status_code == 401
    assert client.get("/admin/videos",headers=team).status_code == 401
    assert upload(client, admin).status_code == 401
    assert client.post("/team/login",json={"username":"alice","password":"wrong"}).status_code == 401
    upload(client,team)
    bob = client.post("/team/login",json={"username":"bob","password":"password123456"}).json()["token"]
    assert client.get("/public/uploads/mine?uploader_name=Alice",headers={"Authorization":f"Bearer {bob}"}).json() == []
    assert "access_token" not in client.get("/public/channels",headers=team).text
    with Session(engine) as session:
        user = session.exec(select(TeamUser).where(TeamUser.username=="alice")).one()
        user.is_active=False
        session.add(user); session.commit()
    assert client.get("/public/channels",headers=team).status_code == 401


def test_validation_and_preview_scope(setup):
    client, engine, admin, team = setup
    vid = upload(client,team).json()["id"]
    assert client.post(f"/admin/videos/{vid}/approve",headers=admin,json={}).status_code == 400
    url = client.get(f"/admin/videos/{vid}/preview-url",headers=admin).json()["url"]
    assert client.get(url.replace(f"/{vid}/preview", "/999/preview")).status_code == 401
    assert client.get(f"/admin/videos/{vid}/preview?token=bad").status_code == 401
    invalid = client.post("/public/uploads",headers=team,data={"title":"x","genre":"x","channel_id":1},files={"file":("x.mp4",b"not video","video/mp4")})
    assert invalid.status_code == 400
    assert client.post("/public/uploads",headers={**team,"Content-Length":str(52*1024*1024)},content=b"x").status_code == 413


def test_oauth_state_browser_binding_and_replay(setup, monkeypatch):
    client, engine, admin, team = setup
    monkeypatch.setattr("app.routers.auth_google.authorization_url",lambda state: f"https://accounts.google.com/auth?state={state}")
    result = client.get("/auth/google/login",headers=admin).json()
    state = result["authorization_url"].split("state=")[1]
    assert client.get(result["authorization_url"],follow_redirects=False).status_code == 307
    assert client.get(result["authorization_url"],follow_redirects=False).status_code == 400
    assert client.get("/auth/google/callback?state=forged&code=code").status_code == 400
    assert client.get(f"/auth/google/callback?state={state}&error=access_denied",follow_redirects=False).status_code == 307
    assert client.get(f"/auth/google/callback?state={state}&code=code").status_code == 400


def test_instagram_processing_persists_container(setup, monkeypatch):
    client, engine, admin, team = setup
    with Session(engine) as session:
        c=session.get(Channel,1); c.platform="instagram"; session.add(c); session.commit()
    vid=upload(client,team).json()["id"]
    approve(client,admin,vid)
    monkeypatch.setattr(meta,"refresh",lambda c:"token")
    monkeypatch.setattr(storage,"signed_url",lambda *a:"https://storage.example/signed")
    create=Mock(return_value="container")
    publish=Mock(return_value="ig-media")
    monkeypatch.setattr(meta,"create_container",create)
    monkeypatch.setattr(meta,"container_status",Mock(side_effect=["IN_PROGRESS","FINISHED"]))
    monkeypatch.setattr(meta,"publish_container",publish)
    monkeypatch.setattr(meta,"permalink",lambda *a:"https://www.instagram.com/reel/test/")
    assert client.post(f"/admin/videos/{vid}/publish",headers=admin,json={}).json()["status"]=="processing"
    assert client.delete(f"/admin/videos/{vid}",headers=admin).status_code==409
    assert client.post(f"/admin/videos/{vid}/publish",headers=admin,json={}).json()["status"]=="published"
    assert create.call_count==1 and publish.call_count==1


def test_uncertain_publish_does_not_retry(setup, monkeypatch):
    client, engine, admin, team=setup
    vid=upload(client,team).json()["id"]; approve(client,admin,vid)
    mock=Mock(side_effect=TimeoutError("secret provider text"))
    monkeypatch.setattr(youtube,"upload_video",mock)
    response=client.post(f"/admin/videos/{vid}/publish",headers=admin,json={})
    assert response.status_code==502 and "secret provider" not in response.text
    assert client.post(f"/admin/videos/{vid}/publish",headers=admin,json={}).status_code==409
    assert mock.call_count==1
    assert client.post(f"/admin/videos/{vid}/reset-publish",headers=admin,json={"confirmed_not_published":True}).status_code==200


def test_encryption_and_retention(setup):
    client, engine, admin, team=setup
    assert unseal(seal("sensitive"))=="sensitive"
    vid=upload(client,team).json()["id"]
    with Session(engine) as session:
        v=session.get(Video,vid); path=v.file_path; v.created_at=datetime.utcnow()-timedelta(days=31)
        session.add(v);session.commit()
    maintenance.cleanup()
    assert not Path(path).exists()
    assert client.get("/admin/videos",headers=admin).json()==[]


def test_youtube_service_respects_visibility_and_checks_identity(tmp_path, monkeypatch):
    path=tmp_path/"clip.mp4";path.write_bytes(MP4)
    channel=Channel(platform="youtube",display_name="test",external_id="right")
    monkeypatch.setattr(youtube,"refresh_if_needed",lambda c:object())
    monkeypatch.setattr(youtube,"fetch_channel_identity",lambda c:{"external_id":"right"})
    api=Mock(); api.videos.return_value.insert.return_value.next_chunk.return_value=(None,{"id":"id"})
    monkeypatch.setattr(youtube,"build",lambda *a,**k:api)
    youtube.upload_video(channel,str(path),"title","description","public",True)
    body=api.videos.return_value.insert.call_args.kwargs["body"]
    assert body["status"]=={"privacyStatus":"public","selfDeclaredMadeForKids":True}
    monkeypatch.setattr(youtube,"fetch_channel_identity",lambda c:{"external_id":"wrong"})
    with pytest.raises(ValueError):
        youtube.upload_video(channel,str(path),"title","")
