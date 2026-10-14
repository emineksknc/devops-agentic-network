"""Denetim izi: tum run'larin Jira aksiyonlari, degistirilemez salt-okunur gorunum."""
from fastapi import APIRouter

from src.api import db

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
async def list_audit(ticket: str = "", repo: str = "", limit: int = 100) -> list[dict]:
    q = """SELECT a.id, a.run_id, r.repo, r.trigger, r.created_at, a.commit_sha, a.ticket_id,
             a.review_passed, a.state, a.comment_ok, a.transition_from, a.transition_to,
             a.transition_ok, a.skipped_reason
           FROM jira_actions a JOIN runs r ON r.id=a.run_id WHERE 1=1"""
    args: list = []
    if ticket:
        q += " AND a.ticket_id LIKE ?"
        args.append(f"%{ticket}%")
    if repo:
        q += " AND r.repo LIKE ?"
        args.append(f"%{repo}%")
    q += " ORDER BY a.id DESC LIMIT ?"
    args.append(max(1, min(limit, 500)))
    with db.connect() as conn:
        rows = conn.execute(q, args).fetchall()
    return [dict(r) for r in rows]
