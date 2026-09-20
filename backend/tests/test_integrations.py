from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
import httpx
import pytest
from fastapi import HTTPException
from sqlmodel import Session, select
from test_workflow import setup, upload, approve
from app.config import settings
from app.crypto import seal, unseal
from app.models import Channel, Video
from app.services import storage, meta, youtube


def response(data, status=200):
    return httpx.Response(status, json=data, request=httpx.Request("GET","https://example.test"))


def test_supabase_private_object_upload_sign_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(settings,"supabase_url","https://project.supabase.co")
    monkeypatch.setattr(settings,"supabase_service_role_key","server-only-key")
    path=tmp_path/"clip.mp4";path.write_bytes(b"content")
    post=Mock(side_effect=[response({"Key":"videos/clip.mp4"}),response({"signedURL":"/object/sign/videos/clip.mp4?token=short"})])
    monkeypatch.setattr(storage.httpx,"post",post)
    key=storage.save(path)
    assert key=="supabase:clip.mp4" and not path.exists()
    url=storage.signed_url(key,900)
    assert url=="https://project.supabase.co/storage/v1/object/sign/videos/clip.mp4?token=short"
    assert post.call_args.kwargs["json"]=={"expiresIn":900}
    assert post.call_args.kwargs["headers"]["Authorization"]=="Bearer server-only-key"
    delete=Mock(return_value=response([]));monkeypatch.setattr(storage.httpx,"request",delete)
    storage.delete(key)
    assert delete.call_args.kwargs["json"]=={"prefixes":["clip.mp4"]}


def test_storage_upload_failure_keeps_local_cleanup_possible(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,"supabase_url","https://project.supabase.co")
    path=tmp_path/"clip.mp4";path.write_bytes(b"content")
    monkeypatch.setattr(storage.httpx,"post",lambda *a,**k:response({"error":"quota"},400))
    with pytest.raises(HTTPException):storage.save(path)
    assert path.exists()


def test_instagram_token_exchange_and_refresh(monkeypatch):
    post=Mock(return_value=response({"access_token":"short","user_id":"ig"}))
    get=Mock(return_value=response({"access_token":"long","expires_in":5184000}))
    monkeypatch.setattr(meta.httpx,"post",post);monkeypatch.setattr(meta.httpx,"get",get)
    assert meta.exchange("authorization-code")["access_token"]=="long"
    assert post.call_args.kwargs["data"]["grant_type"]=="authorization_code"
    assert get.call_args.kwargs["params"]["grant_type"]=="ig_exchange_token"
    channel=Channel(platform="instagram",display_name="ig",external_id="ig",access_token=seal("old"),token_expiry=datetime.utcnow()+timedelta(days=2))
    monkeypatch.setattr(meta,"identity",lambda token:{"user_id":"ig","username":"name"})
    assert meta.refresh(channel)=="long"
    assert unseal(channel.access_token)=="long"
    assert channel.token_expiry > datetime.utcnow()+timedelta(days=50)
    assert get.call_args.kwargs["params"]["grant_type"]=="ig_refresh_token"


def test_instagram_request_shape_and_safe_errors(monkeypatch):
    request=Mock(return_value=response({"id":"container"}))
    monkeypatch.setattr(meta.httpx,"request",request)
    channel=Channel(platform="instagram",display_name="ig",external_id="123")
    video=Video(uploader_name="user",genre="genre",title="Title",description="Caption",channel_id=1,file_path="supabase:file.mp4")
    assert meta.create_container(channel,"secret",video,"https://signed.test")=="container"
    assert request.call_args.args[1].endswith("/123/media")
    assert request.call_args.kwargs["data"]["media_type"]=="REELS"
    assert request.call_args.kwargs["headers"]["Authorization"]=="Bearer secret"
    with pytest.raises(HTTPException) as exc:
        meta.decode(response({"error":{"message":"leaked-token","code":190}},400))
    assert "leaked-token" not in str(exc.value.detail)
    assert "190" in str(exc.value.detail)


def test_instagram_callback_saves_encrypted_account(setup,monkeypatch):
    client,engine,admin,team=setup
    result=client.get("/auth/meta/login",headers=admin).json()
    state=result["authorization_url"].split("state=")[1]
    client.get(result["authorization_url"],follow_redirects=False)
    monkeypatch.setattr(meta,"exchange",lambda code:{"access_token":"ig-token","expires_in":5184000})
    monkeypatch.setattr(meta,"identity",lambda token:{"user_id":"456","username":"my_instagram"})
    result=client.get(f"/auth/meta/callback?state={state}&code=code",follow_redirects=False)
    assert result.status_code==307
    with Session(engine) as session:
        channel=session.exec(select(Channel).where(Channel.platform=="instagram")).one()
        assert channel.external_id=="456" and channel.is_connected
        assert channel.access_token.startswith("enc:") and unseal(channel.access_token)=="ig-token"


def test_instagram_expired_container_can_be_recreated(setup,monkeypatch):
    client,engine,admin,team=setup
    with Session(engine) as session:
        channel=session.get(Channel,1);channel.platform="instagram";session.add(channel);session.commit()
    vid=upload(client,team).json()["id"];approve(client,admin,vid)
    monkeypatch.setattr(meta,"refresh",lambda c:"token")
    monkeypatch.setattr(storage,"signed_url",lambda *a:"https://signed.test")
    create=Mock(side_effect=["expired-container","new-container"])
    monkeypatch.setattr(meta,"create_container",create)
    monkeypatch.setattr(meta,"container_status",Mock(side_effect=["EXPIRED","FINISHED"]))
    monkeypatch.setattr(meta,"publish_container",lambda *a:"published-id")
    monkeypatch.setattr(meta,"permalink",lambda *a:None)
    assert client.post(f"/admin/videos/{vid}/publish",headers=admin,json={}).status_code==502
    with Session(engine) as session:assert session.get(Video,vid).meta_container_id is None
    assert client.post(f"/admin/videos/{vid}/publish",headers=admin,json={}).json()["status"]=="published"
    assert create.call_count==2


def test_disconnect_erases_credentials_and_private_files(setup,monkeypatch):
    client,engine,admin,team=setup
    vid=upload(client,team).json()["id"]
    with Session(engine) as session:path=session.get(Video,vid).file_path
    monkeypatch.setattr("app.routers.channels.httpx.post",lambda *a,**k:response({}))
    assert client.delete("/admin/channels/1",headers=admin).status_code==200
    with Session(engine) as session:
        assert session.get(Channel,1) is None
        assert session.get(Video,vid) is None
    assert not Path(path).exists()


def test_selected_public_visibility_reaches_provider(setup,monkeypatch):
    client,engine,admin,team=setup
    vid=upload(client,team).json()["id"];approve(client,admin,vid)
    call=Mock(return_value={"video_id":"id","url":"https://youtube.com/watch?v=id","privacy_status":"private"})
    monkeypatch.setattr(youtube,"upload_video",call)
    assert client.post(f"/admin/videos/{vid}/publish",headers=admin,json={"privacy_status":"public"}).status_code==200
    assert call.call_args.args[4]=="public"
    # Provider-enforced private state is displayed instead of claiming public.
    assert client.get("/admin/videos?status=published",headers=admin).json()[0]["privacy_status"]=="private"


def test_google_callback_keeps_channel_credentials_encrypted(setup,monkeypatch):
    client,engine,admin,team=setup
    monkeypatch.setattr("app.routers.auth_google.authorization_url",lambda state:f"https://accounts.google.com/auth?state={state}")
    start=client.get("/auth/google/login",headers=admin).json()["authorization_url"]
    state=start.split("state=")[1]
    client.get(start,follow_redirects=False)
    creds=Mock(token="google-token",refresh_token="google-refresh",expiry=datetime.utcnow()+timedelta(hours=1),scopes=["scope"])
    flow=Mock(credentials=creds)
    monkeypatch.setattr(youtube,"build_flow",lambda **kw:flow)
    monkeypatch.setattr(youtube,"fetch_channel_identity",lambda c:{"external_id":"yt-1","title":"Right Channel"})
    assert client.get(f"/auth/google/callback?state={state}&code=code",follow_redirects=False).status_code==307
    with Session(engine) as session:
        channel=session.get(Channel,1)
        assert channel.display_name=="Right Channel"
        assert unseal(channel.refresh_token)=="google-refresh"
        assert channel.access_token.startswith("enc:")


def test_login_rate_limit(setup):
    client,engine,admin,team=setup
    results=[client.post("/admin/login",json={"username":"wrong","password":"wrong"}).status_code for _ in range(21)]
    assert 429 in results
