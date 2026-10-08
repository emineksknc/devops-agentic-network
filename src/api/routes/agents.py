"""Ajan yonetimi: liste, ac/kapa, system prompt override."""
from fastapi import APIRouter
from pydantic import BaseModel

from src.api import db
from src.core.registry import registry

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentUpdate(BaseModel):
    enabled: bool | None = None
    system_prompt: str | None = None


@router.get("")
async def list_agents() -> list[dict]:
    # Registry varsayilanlari yuklensin diye dokun
    from src.agents.orchestrator_agent import _register_defaults

    _register_defaults()
    out = []
    with db.connect() as conn:
        rows = {r["agent_name"]: dict(r) for r in conn.execute("SELECT * FROM agent_configs").fetchall()}
    for name in ("github_agent", "reviewer_agent", "jira_agent", "reporter_agent", "orchestrator"):
        ov = rows.get(name, {})
        out.append({
            "name": name,
            "enabled": bool(ov.get("enabled", 1)) if ov else registry.is_enabled(name),
            "system_prompt": (ov.get("system_prompt") or "") if ov else "",
            "default_prompt": registry.system_prompt(name),
            "customized": bool((ov.get("system_prompt") or "") if ov else False),
        })
    return out


@router.put("/{name}")
async def update_agent(name: str, body: AgentUpdate) -> dict:
    from src.agents.orchestrator_agent import _register_defaults

    _register_defaults()
    if name not in ("github_agent", "reviewer_agent", "jira_agent", "reporter_agent", "orchestrator"):
        from fastapi import HTTPException

        raise HTTPException(404, "ajan bulunamadi")
    with db.connect() as conn:
        cur = conn.execute("SELECT * FROM agent_configs WHERE agent_name=?", (name,)).fetchone()
        enabled = int(body.enabled) if body.enabled is not None else (cur["enabled"] if cur else 1)
        prompt = body.system_prompt if body.system_prompt is not None else ((cur["system_prompt"] or "") if cur else "")
        conn.execute(
            "INSERT INTO agent_configs (agent_name, enabled, system_prompt) VALUES (?,?,?)"
            " ON CONFLICT(agent_name) DO UPDATE SET enabled=excluded.enabled, system_prompt=excluded.system_prompt",
            (name, enabled, prompt),
        )
    registry.refresh()
    return {"updated": name, "enabled": bool(enabled), "customized": bool(prompt)}
