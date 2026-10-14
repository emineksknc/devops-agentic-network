"""Developer bazinda izlenebilirlik: kim ne yapti.
Veri commit_units.author'dan gelir (GitHub API), ek baglanti gerekmez.
"""
from fastapi import APIRouter

from src.api import db

router = APIRouter(prefix="/api/developers", tags=["developers"])


@router.get("")
async def developer_stats(repo: str = "") -> list[dict]:
    q = """SELECT c.author AS author,
             COUNT(*) AS commits,
             SUM(CASE WHEN c.review_status='FAILED' THEN 1 ELSE 0 END) AS blocked,
             COUNT(DISTINCT r.repo) AS repos,
             MAX(r.created_at) AS last_seen
           FROM commit_units c JOIN runs r ON r.id=c.run_id
           WHERE COALESCE(c.author,'') <> ''"""
    args: list = []
    if repo:
        q += " AND r.repo LIKE ?"
        args.append(f"%{repo}%")
    q += " GROUP BY c.author ORDER BY commits DESC LIMIT 100"
    with db.connect() as conn:
        rows = conn.execute(q, args).fetchall()
        out = []
        for row in rows:
            tickets = conn.execute(
                """SELECT DISTINCT a.ticket_id FROM jira_actions a
                   JOIN commit_units c ON c.run_id=a.run_id AND c.sha=a.commit_sha
                   WHERE c.author=? LIMIT 50""",
                (row["author"],),
            ).fetchall()
            out.append({
                "author": row["author"], "commits": row["commits"],
                "blocked": row["blocked"] or 0, "repos": row["repos"],
                "last_seen": row["last_seen"],
                "tickets": [t["ticket_id"] for t in tickets],
            })
    return out
