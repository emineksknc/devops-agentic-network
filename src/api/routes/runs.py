"""Run yasam dongusu: baslat, listele, detay, onayla."""
import logging
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException

from src.api import db
from src.api.schemas import ApproveIn, CommitUnitOut, JiraActionOut, RunCreate, RunDetailOut, RunOut

logger = logging.getLogger("api.runs")
router = APIRouter(prefix="/api/runs", tags=["runs"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_repo(repo: str) -> dict:
    from src.config.settings import settings

    r = (repo or "").strip()
    # Full URL yapistirilirsa (https://github.com/org/name) normalize et
    r = re.sub(r"^https?://github\.com/", "", r, flags=re.IGNORECASE).strip("/")
    if "/" in r:
        owner, name = r.split("/", 1)
        return {"owner": owner.strip(), "repo": name.strip().removesuffix(".git")}
    return {"owner": settings.GITHUB_OWNER, "repo": r}


async def execute_run(
    run_id: str, repo: str, user_goal: str, dry_run: bool | None, count: int,
    github_conn_id: str = "", jira_conn_id: str = "", llm_conn_id: str = "",
) -> None:
    from src.agents.orchestrator_agent import OrchestratorAgent

    with db.connect() as conn:
        policy = db.row_to_dict(conn.execute("SELECT * FROM policies WHERE repo=?", (repo,)).fetchone()) or {}
        gh_id = github_conn_id or (policy.get("github_conn_id") or "")
        ji_id = jira_conn_id or (policy.get("jira_conn_id") or "")
        gh_conn = db.get_connection(conn, gh_id) if gh_id else None
        ji_conn = db.get_connection(conn, ji_id) if ji_id else None
        ll_conn = db.get_connection(conn, llm_conn_id) if llm_conn_id else None
        gh_conn = gh_conn or db.default_connection(conn, "github") or {}
        ji_conn = ji_conn or db.default_connection(conn, "jira") or {}
        ll_conn = ll_conn or db.default_connection(conn, "llm") or {}
        # Policy kapilari: dry_run yoksa bile FAIL onaya dusebilir
        req_dry = dry_run if dry_run is not None else True
        eff_dry = bool(req_dry or policy.get("dry_run_default", 1))
        gates = {
            "plan_on_fail": True if eff_dry else bool(policy.get("require_approval", 1) or not policy.get("auto_write_fail", 0)),
            "plan_on_pass": True if eff_dry else bool(not policy.get("auto_write_pass", 1)),
        }
        transitions = {
            "pass": policy.get("on_pass_transition") or "In Review",
            "fail": policy.get("on_fail_transition") or "Blocked",
        }
        conn.execute(
            "UPDATE runs SET status='running', dry_run=?, github_conn_id=?, jira_conn_id=?, llm_conn_id=? WHERE id=?",
            (1 if eff_dry else 0, gh_conn.get("id", ""), ji_conn.get("id", ""), ll_conn.get("id", ""), run_id),
        )
    try:
        from datetime import datetime, timezone as _tz

        events: list = []

        def _emit(node: str, message: str, level: str = "info") -> None:
            events.append({"ts": datetime.now(_tz.utc).isoformat(), "node": node,
                           "message": message, "level": level})

        orch = OrchestratorAgent(connections={
            "github": gh_conn, "jira": ji_conn, "llm": ll_conn,
            "gates": gates, "transitions": transitions,
            "ticket_project": policy.get("jira_project") or "",
            "emit": _emit,
        })
        gh = _parse_repo(repo)
        gh["count"] = count
        result = await orch.route_and_execute(user_goal, dry_run=eff_dry, github_context=gh)

        units = result.get("commit_units", []) or []
        planned = result.get("jira_planned", []) or []
        with db.connect() as conn:
            for u in units:
                conn.execute(
                    """INSERT INTO commit_units
                       (run_id, sha, short_sha, message, author, jira_ids, code_changes, review_status, review_comment)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        run_id, u.get("sha"), u.get("short_sha"), u.get("message"),
                        u.get("author"), __import__("json").dumps(u.get("jira_ids", [])),
                        (u.get("code_changes") or "")[:20000],
                        u.get("review_status"), u.get("review_comment"),
                    ),
                )
            for p in planned:
                for tid in p.get("jira_ids", []):
                    conn.execute(
                        """INSERT INTO jira_actions
                           (run_id, commit_sha, ticket_id, review_passed, code_changes, state, target_status)
                           VALUES (?,?,?,?,?,?,?)""",
                        (
                            run_id, p.get("commit_sha"), tid,
                            1 if p.get("review_passed") else 0,
                            (p.get("code_changes") or "")[:20000],
                            "planned", p.get("target_status") or "",
                        ),
                    )
            status = result.get("status", "success")
            if planned:
                status = "pending_approval"
            gh_err = result.get("github_error", "")
            if not units and not planned:
                # Bos run = basari DEGIL: ne oldugu acik yazilir
                status = "failed"
                err_text = gh_err or "GitHub'dan hic commit alinamadi (repo adi/token/scope kontrol et)."
            else:
                err_text = gh_err if gh_err and not units else ""
            for ev in events:
                conn.execute(
                    "INSERT INTO run_events (run_id, created_at, node, level, message) VALUES (?,?,?,?,?)",
                    (run_id, ev["ts"], ev["node"], ev["level"], ev["message"][:2000]),
                )
            conn.execute(
                "UPDATE runs SET status=?, final_report=?, error=? WHERE id=?",
                (status, result.get("final_report", ""), err_text, run_id),
            )
    except Exception as e:  # arka plan gorevi hicbir zaman sessizce olmemeli
        logger.exception("run %s basarisiz", run_id)
        with db.connect() as conn:
            conn.execute("UPDATE runs SET status='failed', error=? WHERE id=?", (str(e)[:2000], run_id))


@router.post("", response_model=RunOut, status_code=202)
async def create_run(body: RunCreate, background: BackgroundTasks) -> RunOut:
    run_id = uuid.uuid4().hex[:6]
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO runs (id, created_at, trigger, repo, user_goal, status, dry_run) VALUES (?,?,?,?,?,?,?)",
            (run_id, _now(), "api", body.repo, body.user_goal, "queued", 1 if body.dry_run is not False else 0),
        )
    background.add_task(
        execute_run, run_id, body.repo, body.user_goal, body.dry_run, body.count,
        body.github_conn_id, body.jira_conn_id, body.llm_conn_id,
    )
    return RunOut(run_id=run_id, repo=body.repo, status="queued",
                  dry_run=True if body.dry_run is None else body.dry_run, created_at=_now())


@router.get("", response_model=list[RunOut])
async def list_runs(repo: str = "", status: str = "") -> list[RunOut]:
    q = """SELECT r.*,
             (SELECT COUNT(*) FROM commit_units c WHERE c.run_id=r.id) AS commit_count,
             (SELECT COUNT(*) FROM commit_units c WHERE c.run_id=r.id AND c.review_status='FAILED') AS blocked_count
           FROM runs r WHERE 1=1"""
    args: list = []
    if repo:
        q += " AND r.repo LIKE ?"
        args.append(f"%{repo}%")
    if status:
        q += " AND r.status=?"
        args.append(status)
    q += " ORDER BY r.created_at DESC LIMIT 100"
    with db.connect() as conn:
        rows = conn.execute(q, args).fetchall()
    return [
        RunOut(
            run_id=r["id"], repo=r["repo"], status=r["status"], dry_run=bool(r["dry_run"]),
            blocked_count=r["blocked_count"], commit_count=r["commit_count"], created_at=r["created_at"],
        )
        for r in rows
    ]


@router.get("/{run_id}", response_model=RunDetailOut)
async def get_run(run_id: str) -> RunDetailOut:
    with db.connect() as conn:
        r = db.row_to_dict(conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
        if not r:
            raise HTTPException(404, "run bulunamadi")
        units = conn.execute("SELECT * FROM commit_units WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        actions = conn.execute("SELECT * FROM jira_actions WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        events = conn.execute("SELECT * FROM run_events WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
    return RunDetailOut(
        run_id=r["id"], repo=r["repo"], status=r["status"], dry_run=bool(r["dry_run"]),
        created_at=r["created_at"], final_report=r.get("final_report"), error=r.get("error"),
        commit_units=[
            CommitUnitOut(
                sha=u["sha"], short_sha=u["short_sha"], message=u["message"], author=u["author"],
                jira_ids=db.loads(u["jira_ids"]), review_status=u["review_status"],
                review_comment=u["review_comment"],
            )
            for u in units
        ],
        jira_actions=[
            JiraActionOut(
                ticket_id=a["ticket_id"], commit_sha=a["commit_sha"],
                review_passed=bool(a["review_passed"]), state=a["state"],
                comment_ok=None if a["comment_ok"] is None else bool(a["comment_ok"]),
                transition_from=a["transition_from"], transition_to=a["transition_to"],
                transition_ok=None if a["transition_ok"] is None else bool(a["transition_ok"]),
                skipped_reason=a["skipped_reason"],
            )
            for a in actions
        ],
        events=[
            RunEventOut(created_at=e["created_at"], node=e["node"] or "",
                        level=e["level"] or "info", message=e["message"] or "")
            for e in events
        ],
    )


@router.post("/{run_id}/approve", response_model=RunDetailOut)
async def approve_run(run_id: str, body: ApproveIn) -> RunDetailOut:
    from src.agents.jira_agent import JiraAgent

    with db.connect() as conn:
        r = db.row_to_dict(conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
        if not r:
            raise HTTPException(404, "run bulunamadi")
        if r["status"] != "pending_approval":
            raise HTTPException(409, f"bu run onay beklemiyor (status={r['status']})")
        planned = conn.execute(
            "SELECT * FROM jira_actions WHERE run_id=? AND state='planned' ORDER BY id", (run_id,)
        ).fetchall()

    if not body.approved:
        with db.connect() as conn:
            conn.execute("UPDATE jira_actions SET state='skipped', skipped_reason='rejected_by_user' WHERE run_id=? AND state='planned'", (run_id,))
            conn.execute("UPDATE runs SET status='rejected' WHERE id=?", (run_id,))
        return await get_run(run_id)

    agent = None
    with db.connect() as conn:
        ji_conn = db.get_connection(conn, r.get("jira_conn_id") or "") if r.get("jira_conn_id") else None
        ji_conn = ji_conn or db.default_connection(conn, "jira") or {}

    agent = JiraAgent(connection=ji_conn)
    for a in planned:
        ctx = {
            "jira_ids": [a["ticket_id"]],
            "action": "both",
            "code_changes": a["code_changes"] or "",
            "review_passed": bool(a["review_passed"]),
            "target_status": a["target_status"] or None,
        }
        try:
            res = await agent.run("Update", context=ctx)
            det = (res.get("details") or {}).get(a["ticket_id"], {})
            if det.get("skipped_reason"):
                state, reason = "skipped", det["skipped_reason"]
                cok, tok, tto = None, None, None
            else:
                state = "applied"
                reason = None
                cok = bool(det.get("comment"))
                tok = bool(det.get("transition"))
                tto = a["target_status"] or ("In Review" if bool(a["review_passed"]) else "Blocked")
        except Exception as e:
            state, reason, cok, tok, tto = "failed", str(e)[:500], False, False, None
        with db.connect() as conn:
            conn.execute(
                """UPDATE jira_actions SET state=?, comment_ok=?, transition_to=?,
                   transition_ok=?, skipped_reason=? WHERE id=?""",
                (state, None if cok is None else int(cok), tto, None if tok is None else int(tok), reason, a["id"]),
            )

    with db.connect() as conn:
        blocked = conn.execute(
            "SELECT COUNT(*) c FROM commit_units WHERE run_id=? AND review_status='FAILED'", (run_id,)
        ).fetchone()["c"]
        conn.execute(
            "UPDATE runs SET status=? WHERE id=?",
            ("partially_blocked" if blocked else "success", run_id),
        )
    return await get_run(run_id)
