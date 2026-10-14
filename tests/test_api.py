"""API + cekirdek icin hizli testler. Calistirma: pytest -q
Not: DB her testte temp dosyaya alinir, gercek data/dan.db'ye dokunulmaz.
"""
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
        # Testler admin oturumuyla kosar; kilitsiz cagrilar BAD ile denenir
        c.post("/api/auth/register", json={"username": ADMIN_USER, "password": ADMIN_PASS})
        tok = c.post("/api/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS}).json()["token"]
        c.headers.update({"Authorization": f"Bearer {tok}"})
        yield c


ADMIN_USER, ADMIN_PASS = "sistem-admin", "sistem-parola-1"
BAD = {"Authorization": "Bearer gecersiz-token"}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def _auth_headers(client, username: str, password: str = "guclu-parola-1") -> dict:
    # Kayit davet usuludur: fixture adminiyle acilir (409 yoksayilir), giris yapilir
    client.post("/api/auth/register", json={"username": username, "password": password})
    tok = client.post("/api/auth/login", json={"username": username, "password": password}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def _admin_headers(client) -> dict:
    tok = client.post("/api/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def test_connection_writes_require_admin(client):
    admin = _admin_headers(client)
    viewer = _auth_headers(client, "eleman", "guclu-parola-2")
    body = {"name": "GH", "kind": "github", "base_url": "", "owner": "o", "email": "",
            "token": "", "project_key": "", "provider": "", "model": "",
            "temperature": 0.3, "max_tokens": 2048, "webhook_secret": "", "is_default": False}
    assert client.put("/api/connections/x", json=body, headers=BAD).status_code == 401
    assert client.post("/api/connections", json=body, headers=viewer).status_code == 403
    created = client.post("/api/connections", json=body, headers=admin).json()
    cid = created["id"]
    assert client.delete(f"/api/connections/{cid}", headers=viewer).status_code == 403
    assert client.delete(f"/api/connections/{cid}", headers=admin).json()["deleted"] == cid


def test_approve_requires_approver(client):
    assert client.post("/api/runs/yok/approve", json={"approved": True}, headers=BAD).status_code == 401
    viewer = _auth_headers(client, "eleman", "guclu-parola-2")  # viewer
    r = client.post("/api/runs/yok/approve", json={"approved": True}, headers=viewer)
    assert r.status_code == 403


def test_connections_start_empty_then_create(client):
    # Varsayilan tohum YOK: bos envanterle baslar, UI/API ile eklenir
    assert client.get("/api/connections").json() == []
    admin = _admin_headers(client)
    body = {"name": "GH", "kind": "github", "base_url": "https://api.github.com",
            "owner": "o", "email": "", "token": "secret-token", "project_key": "",
            "provider": "", "model": "", "temperature": 0.3, "max_tokens": 2048,
            "webhook_secret": "", "is_default": True}
    denied = client.post("/api/connections", json=body, headers=BAD)
    assert denied.status_code == 401
    created = client.post("/api/connections", json=body, headers=admin).json()
    assert created["token"] == "***masked***"
    listed = client.get("/api/connections").json()
    assert len(listed) == 1
    for c in listed:
        assert "secret-token" not in c.get("token", "")


def test_policy_crud(client):
    body = {"repo": "org/demo", "jira_project": "SCRUM", "on_pass_transition": "In Review",
            "on_fail_transition": "Blocked", "auto_write_pass": True, "auto_write_fail": False,
            "require_approval": True, "dry_run_default": True,
            "github_conn_id": "", "jira_conn_id": ""}
    assert client.post("/api/policies", json=body).status_code == 200
    assert client.get("/api/policies/org/demo").json()["repo"] == "org/demo"
    assert client.delete("/api/policies/org/demo").status_code == 200
    assert client.get("/api/policies/org/demo").json()["repo"] == "org/demo"


def test_agents_list_and_toggle(client):
    names = {a["name"] for a in client.get("/api/agents").json()}
    assert {"github_agent", "reviewer_agent", "jira_agent", "reporter_agent"} <= names
    assert client.put("/api/agents/reporter_agent", json={"enabled": False}).json()["enabled"] is False
    got = {a["name"]: a for a in client.get("/api/agents").json()}
    assert got["reporter_agent"]["enabled"] is False
    assert client.put("/api/agents/reporter_agent", json={"enabled": True}).json()["enabled"] is True


def test_llm_models_known_provider(client):
    r = client.get("/api/llm/models?provider=openai")
    assert r.status_code == 200
    assert any(m["name"] == "gpt-4o-mini" for m in r.json())


def test_webhook_rejects_unsigned(client):
    r = client.post("/api/webhooks/github", content=b"{}", headers={"X-GitHub-Event": "push"})
    assert r.status_code == 401


def test_audit_empty(client):
    assert client.get("/api/audit").json() == []
    assert client.get("/api/developers").json() == []


def test_redact():
    from src.core import redact as r

    assert r.redact("token ghp_abcdefgh1234567890 done") == "token ***REDACTED*** done"
    assert "secret" in r.redact("api_key = 's3cr3t-value!'").lower() or "***REDACTED***" in r.redact("api_key = 's3cr3t-value!'")


def test_registry_defaults():
    from src.agents.orchestrator_agent import _register_defaults
    from src.core.registry import registry

    _register_defaults()
    assert set(registry.enabled_agents()) >= {"github_agent", "reviewer_agent", "jira_agent", "reporter_agent"}


def test_provider_requires_key():
    import pytest as _p

    from src.core.providers import OpenAIProvider

    with _p.raises(ValueError):
        OpenAIProvider(api_key="")


def test_run_detail_with_events(client):
    # Regresyon: event'li run detay sayfasi 500 vermemeli (RunEventOut importu).
    from src.api import db as dbmod

    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO runs (id, created_at, trigger, repo, user_goal, status, dry_run,"
            " llm_provider, llm_model) VALUES (?,?,?,?,?,?,?,?,?)",
            ("evtest", "2026-01-01T00:00:00+00:00", "api", "org/demo", "", "success", 1,
             "ollama", "qwen3:14b"),
        )
        conn.execute(
            "INSERT INTO run_events (run_id, created_at, node, level, message) VALUES (?,?,?,?,?)",
            ("evtest", "2026-01-01T00:00:01+00:00", "plan", "info", "Plan: github_agent"),
        )
        conn.execute(
            "INSERT INTO commit_units (run_id, sha, short_sha, message, author, jira_ids,"
            " review_status, review_comment, jira_people) VALUES (?,?,?,?,?,?,?,?,?)",
            ("evtest", "abc123", "abc123", "TTA-9 isi", "emineksknc", '["TTA-9"]',
             "PASSED", "Temiz.", '{"TTA-9": {"assignee": "Ayse Atanan", "creator": "Mehmet Olusturan"}}'),
        )
    r = client.get("/api/runs/evtest")
    assert r.status_code == 200
    body = r.json()
    assert len(body["events"]) == 1
    assert body["events"][0]["node"] == "plan"
    # Kisi muhrü detayda doner
    assert body["commit_units"][0]["jira_people"] == {
        "TTA-9": {"assignee": "Ayse Atanan", "creator": "Mehmet Olusturan"}}
    # LLM muhrü listede ve detayda doner
    assert body["llm_provider"] == "ollama"
    assert body["llm_model"] == "qwen3:14b"
    assert "jira_base_url" in body
    listed = client.get("/api/runs").json()
    row = next(x for x in listed if x["run_id"] == "evtest")
    assert row["llm_model"] == "qwen3:14b"


def test_run_list_verdict_flags(client):
    from src.api import db as dbmod

    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO runs (id, created_at, trigger, repo, user_goal, status, dry_run)"
            " VALUES (?,?,?,?,?,?,?)",
            ("flg", "2026-01-02T00:00:00+00:00", "api", "org/demo", "", "success", 1),
        )
        conn.execute(
            "INSERT INTO commit_units (run_id, sha, short_sha, review_status) VALUES (?,?,?,?)",
            ("flg", "a", "a", "FAILED"),
        )
        conn.execute(
            "INSERT INTO commit_units (run_id, sha, short_sha, review_status) VALUES (?,?,?,?)",
            ("flg", "b", "b", "MISMATCH"),
        )
    row = next(x for x in client.get("/api/runs").json() if x["run_id"] == "flg")
    assert row["failed_count"] == 1
    assert row["mismatch_count"] == 1
    assert row["blocked_count"] == 2


def test_duration_seconds():
    from src.api.routes.runs import duration_seconds

    assert duration_seconds("2026-10-14T10:00:00+00:00", "2026-10-14T10:05:30+00:00") == 330
    assert duration_seconds("2026-10-14T10:00:00+00:00", "") is None
    assert duration_seconds("", "") is None
    assert duration_seconds("gecersiz", "2026-10-14T10:05:30+00:00") is None
    # Bitis baslangictan onceyse negatif degil sifir
    assert duration_seconds("2026-10-14T10:05:30+00:00", "2026-10-14T10:00:00+00:00") == 0


def test_run_detail_reports_finish_time_and_duration(client):
    from src.api import db as dbmod

    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO runs (id, created_at, trigger, repo, user_goal, status, dry_run,"
            " finished_at) VALUES (?,?,?,?,?,?,?,?)",
            ("sure", "2026-10-14T10:00:00+00:00", "api", "org/demo", "", "success", 1,
             "2026-10-14T10:04:05+00:00"),
        )
    body = client.get("/api/runs/sure").json()
    assert body["finished_at"] == "2026-10-14T10:04:05+00:00"
    assert body["duration_seconds"] == 245
