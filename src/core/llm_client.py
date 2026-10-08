import logging
from typing import Any, Dict
from src.config.settings import settings
from src.core import tracing
from src.core.providers import build_provider

logger = logging.getLogger("LLMClient")


class LLMClient:
    """
    Provider-bagimsiz LLM istemcisi: ollama (local), openai, anthropic.
    Baglanti verilmezse env ayarlarina duser. Hata davranisi fail-closed ile
    uyumlu: tum provider hatalari fallback string'e doner.
    """
    def __init__(self, connection: Dict[str, Any] = None):
        c = connection or {}
        self.provider_name = (c.get("provider") or getattr(settings, "LLM_PROVIDER", "ollama")).lower()
        self.model = c.get("model") or getattr(settings, "LLM_MODEL", "llama3")
        try:
            self.temperature = float(c.get("temperature") or 0.3)
        except (TypeError, ValueError):
            self.temperature = 0.3
        try:
            self.max_tokens = int(c.get("max_tokens") or 2048)
        except (TypeError, ValueError):
            self.max_tokens = 2048
        self.provider = build_provider(self.provider_name, c, settings)

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = None,
        trace_name: str = "llm",
        trace_meta: dict = None,
    ) -> str:
        """
        response_format="json" verilirse provider'in native JSON modu zorlanir.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            with tracing.generation(
                trace_name, f"{self.provider_name}:{self.model}",
                system_prompt, user_prompt,
                {**(trace_meta or {}), "provider": self.provider_name},
            ) as span:
                try:
                    content = await self.provider.chat(
                        model=self.model,
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        json_mode=(response_format == "json"),
                    )

                    if not content or not content.strip():
                        raise ValueError(f"{self.provider_name} boş bir yanıt döndürdü (content boş).")

                    span["output"] = content
                    return content
                except Exception as e:
                    span["error"] = e
                    raise
        except Exception as e:
            logger.error(f"LLM ({self.provider_name}) hatasi: {str(e)}")
            return "⚠️ Teknik bülten oluşturulurken lokal AI modeline bağlanılamadı."
