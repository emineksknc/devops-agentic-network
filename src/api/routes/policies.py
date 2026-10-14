"""Policy CRUD: repo -> Jira yonetisim kurallari."""
from fastapi import APIRouter, HTTPException

from src.api import db
from src.api.schemas import PolicyIn, PolicyOut

router = APIRouter(prefix="/api/policies", tags=["policies"])


def _row_to_policy(r) -> PolicyOut:
    return PolicyOut(
        repo=r["repo"], jira_project=r["jira_project"],
        on_pass_transition=r["on_pass_transition"], on_fail_transition=r["on_fail_transition"],
        auto_write_pass=bool(r["auto_write_pass"]), auto_write_fail=bool(r["auto_write_fail"]),
        require_approval=bool(r["require_approval"]), dry_run_default=bool(r["dry_run_default"]),
        github_conn_id=r["github_conn_id"] or "", jira_conn_id=r["jira_conn_id"] or "",
    )


@router.get("", response_model=list[PolicyOut])
async def list_policies() -> list[PolicyOut]:
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM policies ORDER BY repo").fetchall()
    return [_row_to_policy(r) for r in rows]


@router.get("/{repo:path}", response_model=PolicyOut)
async def get_policy(repo: str) -> PolicyOut:
    with db.connect() as conn:
        r = db.row_to_dict(conn.execute("SELECT * FROM policies WHERE repo=?", (repo,)).fetchone())
    if not r:
        return PolicyOut(repo=repo, jira_project="")
    return _row_to_policy(r)


@router.post("", response_model=PolicyOut)
async def upsert_policy(body: PolicyIn) -> PolicyOut:
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO policies
               (repo, jira_project, on_pass_transition, on_fail_transition,
                auto_write_pass, auto_write_fail, require_approval, dry_run_default,
                github_conn_id, jira_conn_id)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(repo) DO UPDATE SET
                 jira_project=excluded.jira_project,
                 on_pass_transition=excluded.on_pass_transition,
                 on_fail_transition=excluded.on_fail_transition,
                 auto_write_pass=excluded.auto_write_pass,
                 auto_write_fail=excluded.auto_write_fail,
                 require_approval=excluded.require_approval,
                 dry_run_default=excluded.dry_run_default,
                 github_conn_id=excluded.github_conn_id,
                 jira_conn_id=excluded.jira_conn_id""",
            (
                body.repo, body.jira_project, body.on_pass_transition, body.on_fail_transition,
                int(body.auto_write_pass), int(body.auto_write_fail),
                int(body.require_approval), int(body.dry_run_default),
                body.github_conn_id, body.jira_conn_id,
            ),
        )
    return PolicyOut(**body.model_dump())


@router.delete("/{repo:path}")
async def delete_policy(repo: str) -> dict:
    with db.connect() as conn:
        cur = conn.execute("DELETE FROM policies WHERE repo=?", (repo,))
        if cur.rowcount == 0:
            raise HTTPException(404, "policy bulunamadi")
    return {"deleted": repo}
