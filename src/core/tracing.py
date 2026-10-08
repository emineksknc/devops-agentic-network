"""LangFuse gozlemlenebilirlik katmani.
Paket yoksa veya anahtarlar tanimsizsa tamamen no-op calisir; uretimi kirmaz.
Aktifse her LLM cagrisi icin trace+generation uretir.
"""
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Generator, Optional

from src.config.settings import settings

logger = logging.getLogger("tracing")

_client: Any = None
_checked = False


def _get_client() -> Optional[Any]:
    global _client, _checked
    if _checked:
        return _client
    _checked = True
    secret = getattr(settings, "LANGFUSE_SECRET_KEY", "")
    public = getattr(settings, "LANGFUSE_PUBLIC_KEY", "")
    host = getattr(settings, "LANGFUSE_HOST", "https://cloud.langfuse.com")
    if not secret or not public or secret.startswith("mock") or public.startswith("mock"):
        return None
    try:
        from langfuse import Langfuse

        _client = Langfuse(secret_key=secret, public_key=public, host=host)
        logger.info("LangFuse tracing aktif: %s", host)
    except Exception as e:
        logger.warning("LangFuse baslatilamadi, tracing kapali: %s", e)
        _client = None
    return _client


def is_enabled() -> bool:
    return _get_client() is not None


@contextmanager
def generation(
    name: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    metadata: Optional[dict[str, Any]] = None,
) -> Generator[dict[str, Any], None, None]:
    """Kullanim:
        with tracing.generation("reviewer", model, sys, user) as span:
            out = await llm(...)
            span["output"] = out
    Kapaliysa bos dict verir, maliyeti sifirdir.
    """
    client = _get_client()
    span: dict[str, Any] = {"output": None, "error": None}
    if client is None:
        yield span
        return
    trace_id = uuid.uuid4().hex
    start = time.time()
    try:
        trace = client.trace(id=trace_id, name=f"dan.{name}", metadata=metadata or {})
        gen = trace.generation(
            name=name, model=model,
            input=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            metadata=metadata or {},
        )
    except Exception as e:
        logger.warning("LangFuse span acilamadi: %s", e)
        yield span
        return
    try:
        yield span
    finally:
        try:
            gen.end(
                output=span.get("output"),
                level="ERROR" if span.get("error") else "DEFAULT",
                status_message=str(span["error"])[:500] if span.get("error") else None,
            )
            trace.update(metadata={**(metadata or {}), "latency_s": round(time.time() - start, 3)})
            client.flush()
        except Exception as e:
            logger.warning("LangFuse span kapatilamadi: %s", e)
