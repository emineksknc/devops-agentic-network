"""Dis envanter: baglantilardaki GERCEK GitHub repo'lari ve Jira projeleri.
Politika/run modal'larindaki secimler buradan beslenir; elle yazma kalmaz.
"""
import httpx
from fastapi import APIRouter, HTTPException

from src.api import db

router = APIRouter(tags=["inventory"])


def _conn_or_default(conn_id: str, kind: str) -> dict:
    with db.connect() as conn:
        c = db.get_connection(conn, conn_id) if conn_id else None
        c = c or db.default_connection(conn, kind) or {}
    return dict(c)


def _real_token(c: dict) -> str:
    tok = (c.get("token") or "").strip()
    return "" if tok in ("", "mock_github_token", "mock_jira_token", "***masked***") else tok


@router.get("/api/github/repos")
async def list_repos(conn_id: str = "") -> list[dict]:
    c = _conn_or_default(conn_id, "github")
    token = _real_token(c)
    if not token:
        raise HTTPException(400, "once gecerli bir GitHub baglantisi ekle (Ayarlar)")
    base = (c.get("base_url") or "https://api.github.com").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            out: list[dict] = []
            url: str | None = f"{base}/user/repos?per_page=100&sort=updated"
            while url and len(out) < 300:
                r = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}", "User-Agent": "DAN",
                             "Accept": "application/vnd.github+json"},
                )
                if r.status_code != 200:
                    raise HTTPException(r.status_code, f"github: {r.text[:200]}")
                out.extend({"full_name": x.get("full_name", ""), "private": bool(x.get("private")),
                            "default_branch": x.get("default_branch", "main")}
                           for x in r.json())
                nxt = r.links.get("next", {}).get("url") if hasattr(r, "links") else None
                url = nxt
        return [x for x in out if x["full_name"]]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"github erisilemedi: {e}")


@router.get("/api/jira/projects")
async def list_projects(conn_id: str = "") -> list[dict]:
    c = _conn_or_default(conn_id, "jira")
    token = _real_token(c)
    if not token:
        raise HTTPException(400, "once gecerli bir Jira baglantisi ekle (Ayarlar)")
    base = (c.get("base_url") or "").rstrip("/")
    if not base:
        raise HTTPException(400, "jira base_url bos")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                f"{base}/rest/api/3/project/search?maxResults=50",
                auth=(c.get("email") or "", token),
                headers={"Accept": "application/json"},
            )
            if r.status_code != 200:
                raise HTTPException(r.status_code, f"jira: {r.text[:200]}")
            return [{"key": x.get("key", ""), "name": x.get("name", "")}
                    for x in r.json().get("values", []) if x.get("key")]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"jira erisilemedi: {e}")
