import runpy
import sys
from pathlib import Path
from sqlmodel import Session, select
from test_workflow import setup
from app.models import AdminUser
from app.security import hash_password


def test_two_admins_and_session_revocation(setup):
    client, engine, env_admin, team = setup
    with Session(engine) as session:
        for name in ("admin1", "admin2"):
            session.add(AdminUser(username=name, display_name=name, password_hash=hash_password("admin-password-123")))
        session.commit()
    headers = []
    for name in ("admin1", "admin2"):
        response = client.post("/admin/login", json={"username":name, "password":"admin-password-123"})
        assert response.status_code == 200
        auth = {"Authorization": "Bearer " + response.json()["token"]}
        assert client.get("/admin/videos", headers=auth).status_code == 200
        assert client.get("/public/uploads/mine", headers=auth).status_code == 401
        headers.append(auth)
    assert client.post("/admin/login", json={"username":"alice", "password":"password123456"}).status_code == 401
    with Session(engine) as session:
        first = session.exec(select(AdminUser).where(AdminUser.username == "admin1")).one()
        first.password_hash = hash_password("replacement-password")
        second = session.exec(select(AdminUser).where(AdminUser.username == "admin2")).one()
        second.is_active = False
        session.add(first); session.add(second); session.commit()
    for auth in headers:
        assert client.get("/admin/videos", headers=auth).status_code == 401
    assert client.get("/admin/videos", headers=env_admin).status_code == 200


def test_admin_creation_command(setup, monkeypatch):
    client, engine, _, _ = setup
    monkeypatch.setattr(sys, "argv", ["manage_user.py", "admin1", "--admin", "--name", "Test Admin 1"])
    monkeypatch.setattr("getpass.getpass", lambda prompt: "admin-password-123")
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "manage_user.py"), run_name="__main__")
    with Session(engine) as session:
        admin = session.exec(select(AdminUser).where(AdminUser.username == "admin1")).one()
        assert admin.display_name == "Test Admin 1"
        assert admin.password_hash != "admin-password-123"
    assert client.post("/admin/login", json={"username":"admin1", "password":"admin-password-123"}).status_code == 200
