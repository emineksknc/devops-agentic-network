"""LLM envanteri: Ollama host'undaki kurulu modelleri listeler.
Settings'teki model dropdown'i buradan beslenir; elle yazma devri biter.
"""
import httpx
from fastapi import APIRouter, HTTPException

from src.api import db
from src.config.settings import settings

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/models")
async def list_models(conn_id: str = "", provider: str = "") -> list[dict]:
    host = getattr(settings, "OLLAMA_HOST", "http://localhost:11434")
    provider = (provider or "ollama").lower()
    if conn_id:
        with db.connect() as conn:
            c = db.get_connection(conn, conn_id)
            if not c:
                raise HTTPException(404, "baglanti bulunamadi")
            host = c.get("base_url") or host
            provider = (c.get("provider") or provider or "ollama").lower()
    if provider != "ollama":
        # Cloud provider'larda model listesi API'den gelmez; bilinenler UI'da sabit
        known = {
            "openai": ["gpt-4o-mini", "gpt-4o", "o4-mini"],
            "anthropic": ["claude-sonnet-4-5", "claude-haiku-4-5"],
        }
        return [{"name": m, "source": "known"} for m in known.get(provider, [])]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{host.rstrip('/')}/api/tags")
            r.raise_for_status()
            models = r.json().get("models", [])
        return [{"name": m.get("name", ""), "size_gb": round((m.get("size") or 0) / 1e9, 1), "source": "ollama"} for m in models]
    except Exception as e:
        raise HTTPException(502, f"ollama host'una ulasilamadi ({host}): {e}")
