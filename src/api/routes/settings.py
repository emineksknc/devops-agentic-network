"""Global uygulama ayarlari (anahtar-deger)."""
from fastapi import APIRouter
from pydantic import BaseModel

from src.api import db

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsIn(BaseModel):
    redact_secrets: bool | None = None


@router.get("")
async def get_settings() -> dict:
    with db.connect() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    out = {r["key"]: r["value"] for r in rows}
    out.setdefault("redact_secrets", "1")
    return {"redact_secrets": out["redact_secrets"] not in ("0", "false", "no")}


@router.put("")
async def update_settings(body: SettingsIn) -> dict:
    with db.connect() as conn:
        if body.redact_secrets is not None:
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES ('redact_secrets', ?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("1" if body.redact_secrets else "0",),
            )
    return await get_settings()
