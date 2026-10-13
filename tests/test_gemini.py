"""Gemini dogrudan provider: istek sekli + yanit parse + fail-closed."""
import asyncio

import httpx
import pytest

from src.core.providers import GeminiProvider, build_provider


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
    last_kwargs = None
    response = None

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **kwargs):
        _Client.last_kwargs = {"url": url, **kwargs}
        return _Client.response


def _settings():
    return type("S", (), {"LLM_API_KEY": ""})()


def test_build_provider_gemini():
    p = build_provider("gemini", {"token": "k"}, _settings())
    assert isinstance(p, GeminiProvider)


def test_missing_key_raises():
    with pytest.raises(ValueError):
        GeminiProvider(api_key="")


def test_chat_request_shape_and_parse(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    _Client.response = _Resp(200, {"candidates": [{"content": {"parts": [{"text": '{"review_status": "PASSED"}'}]}}]})
    p = GeminiProvider(api_key="k")
    out = asyncio.run(p.chat(model="gemini-2.0-flash",
                             messages=[{"role": "system", "content": "s"},
                                       {"role": "user", "content": "u"},
                                       {"role": "assistant", "content": "a"}],
                             json_mode=True))
    assert out == '{"review_status": "PASSED"}'
    kw = _Client.last_kwargs
    assert kw["url"].endswith("/v1beta/models/gemini-2.0-flash:generateContent")
    assert kw["headers"]["x-goog-api-key"] == "k"
    assert kw["json"]["system_instruction"]["parts"][0]["text"] == "s"
    assert [c["role"] for c in kw["json"]["contents"]] == ["user", "model"]
    assert kw["json"]["generationConfig"]["responseMimeType"] == "application/json"


def test_api_error_is_fail_closed(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    _Client.response = _Resp(400, {"error": {"message": "API key not valid"}})
    p = GeminiProvider(api_key="k")
    with pytest.raises(ValueError, match="API key not valid"):
        asyncio.run(p.chat(model="gemini-2.0-flash",
                           messages=[{"role": "user", "content": "u"}]))


def test_empty_response_raises(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    _Client.response = _Resp(200, {"candidates": []})
    p = GeminiProvider(api_key="k")
    with pytest.raises(ValueError):
        asyncio.run(p.chat(model="gemini-2.0-flash",
                           messages=[{"role": "user", "content": "u"}]))
