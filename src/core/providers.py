"""Pluggable LLM provider'lar. Yeni bagimlilik yok (httpx + mevcut ollama paketi).
Desteklenenler: ollama (local), openai (+ base_url override ile Azure/custom),
anthropic. Anahtar yoksa/yanlissa fail-closed davranis korunur: hata
yukari firlatilir, LLMClient fallback string'e doner.
"""
import logging
from typing import Any, Dict, List

import httpx

logger = logging.getLogger("providers")


class ChatProvider:
    async def chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        raise NotImplementedError


class OllamaProvider(ChatProvider):
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = (host or "http://localhost:11434").rstrip("/")

    async def chat(self, *, model, messages, temperature=0.3, max_tokens=2048, json_mode=False) -> str:
        import ollama

        try:
            client = ollama.AsyncClient(host=self.host)
        except TypeError:
            client = ollama.AsyncClient()
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            kwargs["format"] = "json"
        try:
            response = await client.chat(**kwargs)
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise ValueError(
                    f"model '{model}' Ollama'da kurulu degil ({self.host}). "
                    f"Kurulu modeller: {await self._installed_models()}. "
                    "Ayarlar'daki LLM baglantisinda modeli guncelle veya 'ollama pull' ile indir."
                ) from e
            raise
        return response["message"]["content"]

    async def _installed_models(self) -> list:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{self.host}/api/tags")
                if r.status_code == 200:
                    return [m.get("name", "") for m in r.json().get("models", [])]
        except Exception:
            pass
        return []


class OpenAIProvider(ChatProvider):
    """OpenAI + Azure OpenAI + OpenAI-uyumlu custom endpoint'ler.
    Azure icin base_url deployment URL'i, model deployment adi olur.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", api_version: str = ""):
        if not api_key:
            raise ValueError("OpenAI provider icin API anahtari sart.")
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.api_version = api_version

    async def chat(self, *, model, messages, temperature=0.3, max_tokens=2048, json_mode=False) -> str:
        url = f"{self.base_url}/chat/completions"
        params = {"api-version": self.api_version} if self.api_version else None
        payload: Dict[str, Any] = {"model": model, "messages": messages,
                                   "temperature": temperature, "max_tokens": max_tokens}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                json=payload,
                params=params,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]


class AnthropicProvider(ChatProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com"):
        if not api_key:
            raise ValueError("Anthropic provider icin API anahtari sart.")
        self.api_key = api_key
        self.base_url = (base_url or "https://api.anthropic.com").rstrip("/")

    async def chat(self, *, model, messages, temperature=0.3, max_tokens=2048, json_mode=False) -> str:
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        turns = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
        if json_mode:
            system += "\nYaniti SADECE gecerli JSON olarak don."
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/messages",
                json={"model": model, "max_tokens": max_tokens, "temperature": temperature,
                      "system": system, "messages": turns},
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            )
            resp.raise_for_status()
            data = resp.json()
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def build_provider(name: str, connection: Dict[str, Any], settings_obj) -> ChatProvider:
    """name: ollama | openai | anthropic. Baglanti degerleri env'nin onune gecer."""
    c = connection or {}
    name = (name or (c.get("provider") or getattr(settings_obj, "LLM_PROVIDER", "ollama"))).lower()
    if name == "openai":
        return OpenAIProvider(
            api_key=c.get("token") or getattr(settings_obj, "LLM_API_KEY", ""),
            base_url=c.get("base_url") or "https://api.openai.com/v1",
        )
    if name == "anthropic":
        return AnthropicProvider(
            api_key=c.get("token") or getattr(settings_obj, "LLM_API_KEY", ""),
            base_url=c.get("base_url") or "https://api.anthropic.com",
        )
    return OllamaProvider(host=c.get("base_url") or getattr(settings_obj, "OLLAMA_HOST", "http://localhost:11434"))
