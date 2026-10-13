"""Kapsam karsilastirmasi: ADF->metin, bilet okuma, reviewer MISMATCH."""
import asyncio

import httpx

from src.agents.jira_agent import JiraAgent, adf_to_text
from src.agents.reviewer_agent import ReviewerAgent

DIFF = "--- Dosya: app.ts ---\n+const x = 1;"
ANALIZ = "Kod temiz, sabit disinda mantik yok."
TICKET = "TTA-9: giris ekrani — kullanici adi ve sifre ile giris yapilabilmeli"


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload

    @property
    def text(self):
        return str(self._payload)


class _Client:
    response = None

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, **kwargs):
        return _Client.response


def _jira():
    return JiraAgent(connection={"base_url": "https://x.atlassian.net", "email": "e",
                                 "token": "t", "project_key": "TTA"})


def test_adf_to_text():
    adf = {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Giris yapilabilmeli."}]},
        {"type": "bulletList", "content": [
            {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Hata mesaji goster."}]}]}]},
    ]}
    text = adf_to_text(adf)
    assert "Giris yapilabilmeli." in text
    assert "Hata mesaji goster." in text
    assert adf_to_text(None) == ""
    assert adf_to_text("duz metin") == "duz metin"


def test_get_issue_text_ok(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    _Client.response = _Resp(200, {"key": "TTA-9", "fields": {
        "summary": "giris ekrani",
        "description": {"type": "doc", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "sifre ile giris"}]}]},
    }})
    out = asyncio.run(_jira().get_issue_text("TTA-9"))
    assert "giris ekrani" in out and "sifre ile giris" in out


def test_get_issue_text_missing_is_empty(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    _Client.response = _Resp(404, {})
    assert asyncio.run(_jira().get_issue_text("TTA-99")) == ""


def test_get_issue_people(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    _Client.response = _Resp(200, {"key": "TTA-9", "fields": {
        "summary": "s", "description": None,
        "assignee": {"displayName": "Ayse Atanan"}, "creator": None}})
    people = asyncio.run(_jira().get_issue_people("TTA-9"))
    assert people == {"assignee": "Ayse Atanan", "creator": "atanmamis"}


class FakeLLM:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    async def generate_response(self, *a, **k):
        return self.outputs.pop(0)


def test_mismatch_accepted_with_ticket_context():
    r = ReviewerAgent(model_client=FakeLLM([
        ANALIZ,
        '{"review_status": "MISMATCH", "affected_file": null, "affected_symbol": null,'
        ' "review_comment": "Bilet giris ekrani istiyor, diff sadece sabit iceriyor."}',
    ]))
    out = asyncio.run(r.run("t", context={"code_changes": DIFF, "ticket_context": TICKET}))
    assert out["review_status"] == "MISMATCH"
    assert "giris" in out["review_comment"].lower()


def test_mismatch_rejected_without_ticket_context():
    r = ReviewerAgent(model_client=FakeLLM([
        ANALIZ,
        '{"review_status": "MISMATCH", "review_comment": "Alakasiz."}',
        '{"review_status": "PASSED", "review_comment": "Temiz."}',
    ]))
    out = asyncio.run(r.run("t", context={"code_changes": DIFF}))
    assert out["review_status"] == "PASSED"


def test_conditional_mismatch_retries_to_concrete():
    # "eger...degilse" ile hukumsuz MISMATCH -> retry -> somut MISMATCH
    r = ReviewerAgent(model_client=FakeLLM([
        ANALIZ,
        '{"review_status": "MISMATCH", "review_comment": "Biletle ilgili degilse MISMATCH olur."}',
        '{"review_status": "MISMATCH", "review_comment": "Bilet giris ekrani istiyor, diff sadece config iceriyor."}',
    ]))
    out = asyncio.run(r.run("t", context={"code_changes": DIFF, "ticket_context": TICKET}))
    assert out["review_status"] == "MISMATCH"
    assert "giris" in out["review_comment"].lower()


def test_double_conditional_is_honest_fail_closed():
    r = ReviewerAgent(model_client=FakeLLM([
        ANALIZ,
        '{"review_status": "MISMATCH", "review_comment": "Eger alakasizsa boyle olur."}',
        '{"review_status": "MISMATCH", "review_comment": "Eger bilet farkliysa yine MISMATCH olur."}',
    ]))
    out = asyncio.run(r.run("t", context={"code_changes": DIFF, "ticket_context": TICKET}))
    assert out["review_status"] == "FAILED"
    assert "2 deneme" in out["review_comment"]
