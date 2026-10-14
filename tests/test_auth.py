"""Faz 1 dilim 1: kayit/login/token/roller. Temp DB, gercege dokunulmaz."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from src.config.settings import settings

    monkeypatch.setattr(settings, "DAN_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "mock")
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "mock")
    from src.api import db as dbmod

    dbmod.init_db()
    from src.api.app import app

    with TestClient(app) as c:
        yield c


def test_first_user_is_admin_second_is_viewer(client):
    a = client.post("/api/auth/register", json={"username": "kurucu", "password": "guclu-parola-1"}).json()
    assert a["role"] == "admin"
    b = client.post("/api/auth/register", json={"username": "izleyici", "password": "guclu-parola-2"}).json()
    assert b["role"] == "viewer"
    dup = client.post("/api/auth/register", json={"username": "kurucu", "password": "baska-parola-3"})
    assert dup.status_code == 409


def test_login_me_logout_cycle(client):
    client.post("/api/auth/register", json={"username": "kurucu", "password": "guclu-parola-1"})
    bad = client.post("/api/auth/login", json={"username": "kurucu", "password": "yanlis-parola"})
    assert bad.status_code == 401
    tok = client.post("/api/auth/login", json={"username": "kurucu", "password": "guclu-parola-1"}).json()
    assert tok["token"].startswith("dan_")
    h = {"Authorization": f"Bearer {tok['token']}"}
    assert client.get("/api/auth/me", headers=h).json()["username"] == "kurucu"
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/logout", headers=h).status_code == 200
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_only_admin_changes_roles(client):
    a = client.post("/api/auth/register", json={"username": "kurucu", "password": "guclu-parola-1"}).json()
    b = client.post("/api/auth/register", json={"username": "eleman", "password": "guclu-parola-2"}).json()
    ta = client.post("/api/auth/login", json={"username": "kurucu", "password": "guclu-parola-1"}).json()["token"]
    tb = client.post("/api/auth/login", json={"username": "eleman", "password": "guclu-parola-2"}).json()["token"]
    ha = {"Authorization": f"Bearer {ta}"}
    hb = {"Authorization": f"Bearer {tb}"}
    denied = client.put(f"/api/auth/users/{b['id']}", json={"role": "approver"}, headers=hb)
    assert denied.status_code == 403
    ok = client.put(f"/api/auth/users/{b['id']}", json={"role": "approver"}, headers=ha).json()
    assert ok["role"] == "approver"
    assert a["role"] == "admin"
