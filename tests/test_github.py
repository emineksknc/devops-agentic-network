"""GitHub yazar: login tercih edilir, baglantisizda gorunen ada dusulur."""
import asyncio

import httpx

from src.agents.github_agent import GitHubAgent


class _Resp:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


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


def _agent():
    return GitHubAgent(connection={"base_url": "https://api.github.com", "token": "t",
                                   "owner": "o"})


def test_author_prefers_login(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    _Client.response = _Resp([{"sha": "abc", "commit": {"message": "m", "author": {"name": "Emine"}},
                              "author": {"login": "emineksknc"}}])
    out = asyncio.run(_agent().fetch_commits("o", "r", 1))
    assert out[0]["author"] == "emineksknc"


def test_author_falls_back_to_name_when_unlinked(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    _Client.response = _Resp([{"sha": "abc", "commit": {"message": "m", "author": {"name": "Emine"}},
                              "author": None}])
    out = asyncio.run(_agent().fetch_commits("o", "r", 1))
    assert out[0]["author"] == "Emine"
