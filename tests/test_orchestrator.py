"""Orkestrator baglanti passthrough: emit callback grafa ulasmali (run timeline)."""
from src.agents.orchestrator_agent import OrchestratorAgent


def test_emit_callback_survives_construction():
    seen = []

    def emit(node, message, level="info"):
        seen.append((node, message, level))

    orch = OrchestratorAgent(connections={"emit": emit})
    assert orch._connections.get("emit") is emit
