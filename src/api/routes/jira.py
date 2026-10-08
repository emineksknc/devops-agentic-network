"""Test tohumlama: Jira'da ornek biletler acar (sadece istendiginde)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api import db
from src.agents.jira_agent import JiraAgent

router = APIRouter(prefix="/api/jira", tags=["jira"])


class SeedIn(BaseModel):
    project_key: str = ""
    summaries: list[str] = []
    jira_conn_id: str = ""


@router.post("/issues/seed")
async def seed_issues(body: SeedIn) -> dict:
    with db.connect() as conn:
        ji = db.get_connection(conn, body.jira_conn_id) if body.jira_conn_id else None
        ji = ji or db.default_connection(conn, "jira") or {}
    project = body.project_key or ji.get("project_key") or ""
    if not project:
        raise HTTPException(400, "project_key sart")
    agent = JiraAgent(connection=ji)
    opened = []
    for s in (body.summaries or [])[:10]:
        key = await agent.create_ticket(project, s, f"[DAN test tohumu] {s}")
        if key:
            opened.append(key)
    return {"opened": opened, "project": project}
