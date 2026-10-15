"""Baglanti envanteri: birden fazla GitHub org / Jira sitesi / LLM.
Token'lar Fernet ile sifreli saklanir (src/core/secrets); API maskeli doner."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

from src.api import db
from src.api.schemas import ConnectionIn, ConnectionOut
from src.core import secrets as secrets_mod
from src.core.auth import require_roles, get_current_user

logger = logging.getLogger("api.connections")

router = APIRouter(prefix="/api/connections", tags=["connections"], dependencies=[Depends(get_current_user)])


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

    def _tri(value):
        # TEXT kolonlardaki 0/1 bayraklari: '0' string'i bool() ile True olur, dikkat
        if value is None or value == "":
            return None
        return str(value) not in ("0", "False", "false")
    return ConnectionOut(
        id=r["id"], name=r["name"], kind=r["kind"], base_url=r["base_url"] or "",
        owner=r["owner"] or "", email=r["email"] or "",
        token=MASKED if r["token"] else "",
        project_key=r["project_key"] or "",
        provider=(r["provider"] or "") if "provider" in keys else "",
        model=(r["model"] or "") if "model" in keys else "",
        temperature=_num(r, "temperature", 0.3) if "temperature" in keys else 0.3,
        max_tokens=int(_num(r, "max_tokens", 2048)) if "max_tokens" in keys else 2048,
        webhook_secret=(MASKED if r["webhook_secret"] else "") if "webhook_secret" in keys else "",
        is_default=bool(r["is_default"]),
        is_disabled=bool(r["is_disabled"]) if "is_disabled" in keys else False,
        created_at=(r["created_at"] or "") if "created_at" in keys else "",
        disabled_at=(r["disabled_at"] or "") if "disabled_at" in keys else "",
        last_tested_at=(r["last_tested_at"] or "") if "last_tested_at" in keys else "",
        last_latency_ms=int(r["last_latency_ms"] or 0) if "last_latency_ms" in keys else 0,
        last_test_ok=_tri(r["last_test_ok"]) if "last_test_ok" in keys else None,
        last_test_status=int(r["last_test_status"] or 0) if "last_test_status" in keys else 0,
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
async def create_connection(body: ConnectionIn, _admin: dict = Depends(require_roles("admin"))) -> ConnectionOut:
    from datetime import datetime, timezone

    conn_id = f"{body.kind}-{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc).isoformat()
    with db.connect() as conn:
        if body.is_default:
            conn.execute("UPDATE connections SET is_default=0 WHERE kind=?", (body.kind,))
        conn.execute(
            "INSERT INTO connections (id, kind, name, base_url, owner, email, token, project_key, provider, model, temperature, max_tokens, webhook_secret, is_default,"
            " is_disabled, created_at, disabled_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (conn_id, body.kind, body.name, body.base_url, body.owner, body.email,
             secrets_mod.encrypt(body.token), body.project_key, body.provider, body.model,
             body.temperature, body.max_tokens, secrets_mod.encrypt(body.webhook_secret), int(body.is_default),
             0, now, ""),
        )
    out = body.model_dump()
    out["token"] = MASKED if body.token else ""
    out["created_at"] = now
    return ConnectionOut(id=conn_id, **out)


@router.put("/{conn_id}", response_model=ConnectionOut)
async def update_connection(conn_id: str, body: ConnectionIn, _admin: dict = Depends(require_roles("admin"))) -> ConnectionOut:
    with db.connect() as conn:
        r = db.row_to_dict(conn.execute("SELECT * FROM connections WHERE id=?", (conn_id,)).fetchone())
        if not r:
            raise HTTPException(404, "baglanti bulunamadi")
        # Maskeli/bos token gelirse mevcut secret korunur (DB'de sifreli durur, oldugu gibi yazilir)
        token = r["token"] if body.token in ("", MASKED) else body.token
        secret = r["webhook_secret"] if body.webhook_secret in ("", MASKED) else body.webhook_secret
        if body.is_default:
            conn.execute("UPDATE connections SET is_default=0 WHERE kind=?", (r["kind"],))
        conn.execute(
            """UPDATE connections SET name=?, base_url=?, owner=?, email=?, token=?,
               project_key=?, provider=?, model=?, temperature=?, max_tokens=?, webhook_secret=?, is_default=? WHERE id=?""",
            (body.name, body.base_url, body.owner, body.email, secrets_mod.encrypt(token),
             body.project_key, body.provider, body.model,
             body.temperature, body.max_tokens, secrets_mod.encrypt(secret), int(body.is_default), conn_id),
        )
    out = body.model_dump()
    out["token"] = MASKED if token else ""
    return ConnectionOut(id=conn_id, **out)


@router.delete("/{conn_id}")
async def delete_connection(conn_id: str, _admin: dict = Depends(require_roles("admin"))) -> dict:
    with db.connect() as conn:
        cur = conn.execute("DELETE FROM connections WHERE id=?", (conn_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "baglanti bulunamadi")
    return {"deleted": conn_id}


@router.post("/{conn_id}/toggle", response_model=ConnectionOut)
async def toggle_connection(conn_id: str, _admin: dict = Depends(require_roles("admin"))) -> ConnectionOut:
    """Aktif/pasif anahtari. Pasif baglanti varsayilan secime girmez, run'lar onu kullanmaz."""
    from datetime import datetime, timezone

    with db.connect() as conn:
        r = db.row_to_dict(conn.execute("SELECT * FROM connections WHERE id=?", (conn_id,)).fetchone())
        if not r:
            raise HTTPException(404, "baglanti bulunamadi")
        cols = {c["name"] for c in conn.execute("PRAGMA table_info(connections)").fetchall()}
        if "is_disabled" not in cols:
            raise HTTPException(409, "DB migrasyonu eksik: server'i yeniden baslat")
        new_disabled = 0 if r.get("is_disabled") else 1
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE connections SET is_disabled=?, disabled_at=? WHERE id=?",
            (new_disabled, now if new_disabled else "", conn_id),
        )
        r = db.row_to_dict(conn.execute("SELECT * FROM connections WHERE id=?", (conn_id,)).fetchone())
    return _to_out(r)


@router.get("/{conn_id}/secret")
async def reveal_secret(
    conn_id: str, field: str = "token",
    _admin: dict = Depends(require_roles("admin")),
) -> dict:
    """Kayitli secret'i TEK SEFERLIK acar (admin'e ozel). Kullanim loga duser;
    liste/get uclari maskeli kalmaya devam eder."""
    if field not in ("token", "webhook_secret"):
        raise HTTPException(400, "alan token/webhook_secret olmali")
    with db.connect() as conn:
        r = db.row_to_dict(conn.execute("SELECT * FROM connections WHERE id=?", (conn_id,)).fetchone())
    if not r:
        raise HTTPException(404, "baglanti bulunamadi")
    logger.warning("Secret goruntulendi: conn=%s field=%s admin=%s",
                   conn_id, field, _admin.get("username", "?"))
    return {"value": secrets_mod.decrypt(r[field] or "")}


@router.post("/{conn_id}/test")
async def test_connection(conn_id: str) -> dict:
    """Salt-okunur canlilik testi: secret'i dogrulamadan dokunmadan dener."""
    import time

    import httpx

    from datetime import datetime, timezone

    with db.connect() as conn:
        r = db.row_to_dict(conn.execute("SELECT * FROM connections WHERE id=?", (conn_id,)).fetchone())
    if not r:
        raise HTTPException(404, "baglanti bulunamadi")
    kind = r["kind"]
    # DB sifreli durur; canli deneme icin coz (maskeleme _to_out'ta ayri yol, etkilenmez)
    token = secrets_mod.decrypt(r["token"] or "")
    t0 = time.perf_counter()

    def finish(ok: bool, status: int, detail: str) -> dict:
        ms = int((time.perf_counter() - t0) * 1000)
        now = datetime.now(timezone.utc).isoformat()
        try:
            with db.connect() as conn:
                conn.execute(
                    "UPDATE connections SET last_tested_at=?, last_latency_ms=?, last_test_ok=?, last_test_status=? WHERE id=?",
                    (now, ms, 1 if ok else 0, status, conn_id),
                )
        except Exception:
            pass
        return {"ok": ok, "status": status, "detail": detail, "latency_ms": ms}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if kind == "github":
                base = (r["base_url"] or "https://api.github.com").rstrip("/")
                resp = await client.get(
                    f"{base}/rate_limit",
                    headers={"Authorization": f"token {token}", "User-Agent": "DAN-test"},
                )
                ok = resp.status_code == 200
                return finish(ok, resp.status_code, "token gecerli" if ok else resp.text[:200])
            if kind == "jira":
                base = (r["base_url"] or "").rstrip("/")
                resp = await client.get(f"{base}/rest/api/3/myself",
                                        auth=(r["email"], token))
                ok = resp.status_code == 200
                return finish(ok, resp.status_code, "baglanti saglam" if ok else resp.text[:200])
            if kind == "llm":
                provider = (r["provider"] or "ollama").lower()
                if provider == "ollama":
                    base = (r["base_url"] or "http://localhost:11434").rstrip("/")
                    resp = await client.get(f"{base}/api/tags")
                    if resp.status_code != 200:
                        return finish(False, resp.status_code, resp.text[:200])
                    names = [m.get("name", "") for m in resp.json().get("models", [])]
                    has = (r["model"] or "") in names
                    return finish(True, 200,
                                  f"{len(names)} model; secili '{r['model']}' " + ("kurulu" if has else "KURULU DEGIL"))
                if provider == "openai":
                    base = (r["base_url"] or "https://api.openai.com/v1").rstrip("/")
                    resp = await client.get(f"{base}/models",
                                            headers={"Authorization": f"Bearer {token}"})
                    ok = resp.status_code == 200
                    return finish(ok, resp.status_code, "anahtar gecerli" if ok else resp.text[:200])
                if provider == "gemini":
                    base = (r["base_url"] or "https://generativelanguage.googleapis.com").rstrip("/")
                    resp = await client.get(f"{base}/v1beta/models",
                                            headers={"x-goog-api-key": token})
                    if resp.status_code != 200:
                        return finish(False, resp.status_code, resp.text[:200])
                    names = [m.get("name", "") for m in resp.json().get("models", [])]
                    return finish(True, 200, f"anahtar gecerli ({len(names)} model listelendi)")
                return finish(False, 0, f"{provider} icin otomatik test yok")
    except Exception as e:
        return finish(False, 0, f"erisilemedi: {e}")
    return finish(False, 0, "bilinmeyen tur")
