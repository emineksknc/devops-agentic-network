"""Ajan registry: hangi ajan aktif, prompt override'leri nereden gelir.
Varsayilanlar kodda; kurumsal ozellestirme DB'deki agent_configs tablosunda.
DB ulasilamazsa varsayilanlarla devam eder (fail-open config, fail-closed review ayri).
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("registry")


@dataclass
class AgentSpec:
    name: str
    enabled: bool = True
    system_prompt: str = ""
    factory: Optional[Callable[..., Any]] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class AgentRegistry:
    def __init__(self):
        self._specs: Dict[str, AgentSpec] = {}
        self._db_overrides: Optional[Dict[str, Dict[str, Any]]] = None

    def register(self, name: str, factory: Callable[..., Any], system_prompt: str = "") -> None:
        self._specs[name] = AgentSpec(name=name, factory=factory, system_prompt=system_prompt)

    def _load_db_overrides(self) -> Dict[str, Dict[str, Any]]:
        if self._db_overrides is not None:
            return self._db_overrides
        self._db_overrides = {}
        try:
            from src.api import db as dbmod

            with dbmod.connect() as conn:
                rows = conn.execute("SELECT * FROM agent_configs").fetchall()
            for r in rows:
                self._db_overrides[r["agent_name"]] = {
                    "enabled": bool(r["enabled"]),
                    "system_prompt": r["system_prompt"] or "",
                }
        except Exception as e:
            logger.warning("agent_configs okunamadi, varsayilanlar kullaniliyor: %s", e)
        return self._db_overrides

    def refresh(self) -> None:
        self._db_overrides = None

    def is_enabled(self, name: str) -> bool:
        spec = self._specs.get(name)
        if spec is None:
            return False
        ov = self._load_db_overrides().get(name, {})
        return ov.get("enabled", spec.enabled)

    def system_prompt(self, name: str) -> str:
        spec = self._specs.get(name)
        base = spec.system_prompt if spec else ""
        ov = self._load_db_overrides().get(name, {})
        return ov.get("system_prompt") or base

    def build(self, name: str, **kwargs) -> Any:
        spec = self._specs.get(name)
        if spec is None or spec.factory is None:
            raise KeyError(f"ajan kayitli degil: {name}")
        return spec.factory(**kwargs)

    def enabled_agents(self) -> list[str]:
        return [n for n in self._specs if self.is_enabled(n)]


registry = AgentRegistry()
