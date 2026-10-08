"""Baglanti envanteri: birden fazla GitHub org / Jira sitesi / LLM.
NOT(v1): token'lar SQLite'da duz metin durur; dosya izni + vault plani sart."""
import uuid

from fastapi import APIRouter, HTTPException

from src.api import db
from src.api.schemas import ConnectionIn, ConnectionOut

router = APIRouter(prefix="/api/connections", tags=["connections"])


MASKED = "***masked***"


def _num(row, key: str, default: float) -> float:
    try:
        v = row[key]
        return float(v) if v not in (None, "") else default
    except (KeyError, TypeError, ValueError):
        return default


def _to_out(r) -> ConnectionOut:
    # Token ASLA listeleme/get ile disari verilmez
    keys = set(r.keys())
    return ConnectionOut(
        id=r["id"], name=r["name"], kind=r["kind"], base_url=r["base_url"] or "",
        owner=r["owner"] or "", email=r["email"] or "",
        token=MASKED if r["token"] else "",
        project_key=r["project_key"] or "",
        provider=(r["provider"] or "") if "provider" in keys else "",
        model=(r["model"] or "") if "model" in keys else "",
        temperature=_num(r, "temperature", 0.3) if "temperature" in keys else 0.3,
        max_tokens=int(_num(r, "max_tokens", 2048)) if "max_tokens" in keys else 2048,
        is_default=bool(r["is_default"]),
    )


@router.get("", response_model=list[ConnectionOut])
async def list_connections(kind: str = "") -> list[ConnectionOut]:
    with db.connect() as conn:
        if kind:
            rows = conn.execute("SELECT * FROM connections WHERE kind=? ORDER BY name", (kind,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM connections ORDER BY kind, name").fetchall()
    return [_to_out(r) for r in rows]


@router.post("", response_model=ConnectionOut, status_code=201)
async def create_connection(body: ConnectionIn) -> ConnectionOut:
    conn_id = f"{body.kind}-{uuid.uuid4().hex[:6]}"
    with db.connect() as conn:
        if body.is_default:
            conn.execute("UPDATE connections SET is_default=0 WHERE kind=?", (body.kind,))
        conn.execute(
            "INSERT INTO connections (id, kind, name, base_url, owner, email, token, project_key, provider, model, temperature, max_tokens, is_default)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (conn_id, body.kind, body.name, body.base_url, body.owner, body.email,
             body.token, body.project_key, body.provider, body.model,
             body.temperature, body.max_tokens, int(body.is_default)),
        )
    out = body.model_dump()
    out["token"] = MASKED if body.token else ""
    return ConnectionOut(id=conn_id, **out)


@router.put("/{conn_id}", response_model=ConnectionOut)
async def update_connection(conn_id: str, body: ConnectionIn) -> ConnectionOut:
    with db.connect() as conn:
        r = db.row_to_dict(conn.execute("SELECT * FROM connections WHERE id=?", (conn_id,)).fetchone())
        if not r:
            raise HTTPException(404, "baglanti bulunamadi")
        # Maskeli/bos token gelirse mevcut secret korunur
        token = r["token"] if body.token in ("", MASKED) else body.token
        if body.is_default:
            conn.execute("UPDATE connections SET is_default=0 WHERE kind=?", (r["kind"],))
        conn.execute(
            """UPDATE connections SET name=?, base_url=?, owner=?, email=?, token=?,
               project_key=?, provider=?, model=?, temperature=?, max_tokens=?, is_default=? WHERE id=?""",
            (body.name, body.base_url, body.owner, body.email, token,
             body.project_key, body.provider, body.model,
             body.temperature, body.max_tokens, int(body.is_default), conn_id),
        )
    out = body.model_dump()
    out["token"] = MASKED if token else ""
    return ConnectionOut(id=conn_id, **out)


@router.delete("/{conn_id}")
async def delete_connection(conn_id: str) -> dict:
    with db.connect() as conn:
        cur = conn.execute("DELETE FROM connections WHERE id=?", (conn_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "baglanti bulunamadi")
    return {"deleted": conn_id}


@router.post("/{conn_id}/test")
async def test_connection(conn_id: str) -> dict:
    """Salt-okunur canlilik testi: secret'i dogrulamadan dokunmadan dener."""
    import httpx

    with db.connect() as conn:
        r = db.row_to_dict(conn.execute("SELECT * FROM connections WHERE id=?", (conn_id,)).fetchone())
    if not r:
        raise HTTPException(404, "baglanti bulunamadi")
    kind = r["kind"]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if kind == "github":
                base = (r["base_url"] or "https://api.github.com").rstrip("/")
                resp = await client.get(
                    f"{base}/rate_limit",
                    headers={"Authorization": f"token {r['token']}", "User-Agent": "DAN-test"},
                )
                ok = resp.status_code == 200
                return {"ok": ok, "status": resp.status_code,
                        "detail": "token gecerli" if ok else resp.text[:200]}
            if kind == "jira":
                base = (r["base_url"] or "").rstrip("/")
                resp = await client.get(f"{base}/rest/api/3/myself",
                                        auth=(r["email"], r["token"]))
                ok = resp.status_code == 200
                return {"ok": ok, "status": resp.status_code,
                        "detail": "baglanti saglam" if ok else resp.text[:200]}
            if kind == "llm":
                provider = (r["provider"] or "ollama").lower()
                if provider == "ollama":
                    base = (r["base_url"] or "http://localhost:11434").rstrip("/")
                    resp = await client.get(f"{base}/api/tags")
                    if resp.status_code != 200:
                        return {"ok": False, "status": resp.status_code, "detail": resp.text[:200]}
                    names = [m.get("name", "") for m in resp.json().get("models", [])]
                    has = (r["model"] or "") in names
                    return {"ok": True, "status": 200,
                            "detail": f"{len(names)} model; secili '{r['model']}' " + ("kurulu" if has else "KURULU DEGIL")}
                if provider == "openai":
                    base = (r["base_url"] or "https://api.openai.com/v1").rstrip("/")
                    resp = await client.get(f"{base}/models",
                                            headers={"Authorization": f"Bearer {r['token']}"})
                    ok = resp.status_code == 200
                    return {"ok": ok, "status": resp.status_code,
                            "detail": "anahtar gecerli" if ok else resp.text[:200]}
                return {"ok": False, "status": 0, "detail": f"{provider} icin otomatik test yok"}
    except Exception as e:
        return {"ok": False, "status": 0, "detail": f"erisilemedi: {e}"}
    return {"ok": False, "status": 0, "detail": "bilinmeyen tur"}
