"""Faz 1 dilim 3: secret sifreleme (Fernet). Temp DB + sabit test anahtari."""
import pytest
from fastapi.testclient import TestClient

# SADECE TEST: gercek bir secret degil, temp DB'ler icin sabit anahtar
TEST_KEY = "0ywO8kJNk2avCqVR4zjw-kWVVdOA5OGUJOQbdo3RkXg="


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from src.config.settings import settings

    monkeypatch.setattr(settings, "DAN_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "mock")
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "mock")
    monkeypatch.setenv("DAN_SECRET_KEY", TEST_KEY)
    from src.api import db as dbmod

    dbmod.init_db()
    from src.api.app import app

    with TestClient(app) as c:
        yield c


def _admin(client):
    client.post("/api/auth/register", json={"username": "testadmin", "password": "guclu-parola-1"})
    tok = client.post("/api/auth/login", json={"username": "testadmin", "password": "guclu-parola-1"}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def test_roundtrip_and_idempotency():
    from src.core import secrets as s

    assert s.decrypt("") == "" and s.encrypt("") == ""
    ct = s.encrypt("gizli-token-123")
    assert ct.startswith("fernet:") and "gizli-token" not in ct
    assert s.decrypt(ct) == "gizli-token-123"
    assert s.encrypt(ct) == ct  # cift sifreleme yok
    assert s.decrypt("acik-metin-legacy") == "acik-metin-legacy"  # migrasyon yolu


def test_tampered_ciphertext_fails_closed():
    from src.core import secrets as s

    ct = s.encrypt("gizli")
    bad = ct[:-4] + ("AAAA" if not ct.endswith("AAAA") else "BBBB")
    with pytest.raises(ValueError):
        s.decrypt(bad)


def test_db_at_rest_is_sealed(client):
    from src.api import db as dbmod

    h = _admin(client)
    body = {"name": "GH", "kind": "github", "base_url": "", "owner": "o", "email": "",
            "token": "cok-gizli-token", "project_key": "", "provider": "", "model": "",
            "temperature": 0.3, "max_tokens": 2048, "webhook_secret": "wh-gizli",
            "is_default": False}
    created = client.post("/api/connections", json=body, headers=h).json()
    with dbmod.connect() as conn:
        row = conn.execute("SELECT token, webhook_secret FROM connections WHERE id=?",
                           (created["id"],)).fetchone()
        assert row["token"].startswith("fernet:") and "cok-gizli" not in row["token"]
        assert row["webhook_secret"].startswith("fernet:")
    # API maskeli doner, cozulmus hal disari sizmaz
    listed = client.get("/api/connections", headers=h).json()
    assert "cok-gizli-token" not in str(listed)
    # Ajan yolu duz metni alir
    with dbmod.connect() as conn:
        conn_row = dbmod.get_connection(conn, created["id"])
    assert conn_row["token"] == "cok-gizli-token"
    assert conn_row["webhook_secret"] == "wh-gizli"


def test_legacy_plaintext_is_migrated(client):
    from src.api import db as dbmod

    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO connections (id, kind, name, token, webhook_secret) VALUES (?,?,?,?,?)",
            ("legacy-1", "github", "Eski", "acik-token", "acik-secret"),
        )
    dbmod.init_db()  # migrasyon tekrar kosar
    with dbmod.connect() as conn:
        row = conn.execute("SELECT token, webhook_secret FROM connections WHERE id='legacy-1'").fetchone()
        assert row["token"].startswith("fernet:")
        assert dbmod.get_connection(conn, "legacy-1")["token"] == "acik-token"
