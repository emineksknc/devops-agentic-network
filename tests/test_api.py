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
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_connections_start_empty_then_create(client):
    # Varsayilan tohum YOK: bos envanterle baslar, UI/API ile eklenir
    assert client.get("/api/connections").json() == []
    body = {"name": "GH", "kind": "github", "base_url": "https://api.github.com",
            "owner": "o", "email": "", "token": "secret-token", "project_key": "",
            "provider": "", "model": "", "temperature": 0.3, "max_tokens": 2048,
            "webhook_secret": "", "is_default": True}
    created = client.post("/api/connections", json=body).json()
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
