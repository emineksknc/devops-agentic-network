"""GitHub webhook alici: push -> otomatik run.
Guvenlik: X-Hub-Signature-256, kayitli tum GitHub secret'lari denenir.
Secret'i olmayan baglanti webhook kabul etmez (401).
"""
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from src.api import db
from src.api.routes.runs import execute_run

logger = logging.getLogger("api.webhooks")
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _match_secret(payload: bytes, signature: str, secrets: list[tuple[str, str]]) -> str:
    """Doner: eslesen baglanti id'si. Yoksa bos."""
    if not signature or not signature.startswith("sha256="):
        return ""
    want = signature.split("=", 1)[1]
    for conn_id, secret in secrets:
        if not secret:
            continue
        got = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        if hmac.compare_digest(got, want):
            return conn_id
    return ""


@router.post("/github", status_code=202)
async def github_push(
    request: Request,
    background: BackgroundTasks,
    signature: str = Header(default="", alias="X-Hub-Signature-256"),
    event: str = Header(default="", alias="X-GitHub-Event"),
) -> dict:
    payload = await request.body()
    with db.connect() as conn:
        conns = conn.execute(
            "SELECT * FROM connections WHERE kind='github' AND webhook_secret <> ''"
        ).fetchall()
        matched = _match_secret(payload, signature, [(c["id"], c["webhook_secret"]) for c in conns])
        if not matched:
            raise HTTPException(401, "webhook imzasi gecersiz veya secret kayitli degil")
    if event and event != "push":
        return {"ignored": event}
    try:
        data = json.loads(payload.decode("utf-8"))
    except Exception:
        raise HTTPException(400, "json okunamadi")
    repo = ((data.get("repository") or {}).get("full_name") or "").strip()
    if not repo:
        raise HTTPException(400, "repository.full_name yok")

    run_id = uuid.uuid4().hex[:6]
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO runs (id, created_at, trigger, repo, user_goal, status, dry_run, github_conn_id)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (run_id, datetime.now(timezone.utc).isoformat(), "webhook", repo,
             "GitHub reposundaki son değişiklikleri incele, ilgili Jira kartlarını güncelle ve teknik bülteni hazırla.",
             "queued", 1, matched),
        )
    background.add_task(execute_run, run_id, repo,
                        "GitHub reposundaki son değişiklikleri incele, ilgili Jira kartlarını güncelle ve teknik bülteni hazırla.",
                        None, 5, matched, "", "")
    logger.info("webhook push: %s -> run %s", repo, run_id)
    return {"run_id": run_id, "repo": repo, "status": "queued"}
