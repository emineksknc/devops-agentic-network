import logging
from typing import Dict, Any
from src.core.base_agent import BaseAgent
from src.core.llm_client import LLMClient
from src.core.registry import registry
from src.agents.github_agent import GitHubAgent
from src.agents.jira_agent import JiraAgent
from src.agents.reporter_agent import ReporterAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.config.settings import settings

logger = logging.getLogger("OrchestratorAgent")

ORCHESTRATOR_PLAN_PROMPT = (
    "Sen bir DevOps Orkestra Sefisin. Elinde su 4 alt ajan (arac) var:\n"
    "1. 'github_agent': Canli depodan son commitleri okur.\n"
    "2. 'reviewer_agent': Kod kalitesi ve guvenlik analizini yapip PASSED/FAILED raporlar.\n"
    "3. 'jira_agent': Bulunan biletleri Jira'da gunceller.\n"
    "4. 'reporter_agent': Commitlerden Turkce surum raporu hazirlar.\n\n"
    "Kullanicinin hedefine bakarak, hangi sirayla hangi ajanlari calistirman gerektigini planla.\n"
    "Yonlendirme Kurallari: Kodlari incelemeden kalite analizi veya jira guncellemesi yapamazsin.\n"
    "Yanıtını SADECE ve SADECE su JSON formatinda don, baska hicbir aciklama yazma:\n"
    "{\n"
    '  "plan": ["ajan_adi_1", "ajan_adi_2"],\n'
    '  "reason": "Bu plani yapma nedenin"\n'
    "}"
)


def _register_defaults() -> None:
    if "github_agent" not in registry._specs:
        from src.agents.reporter_agent import ReporterAgent as _Rep
        from src.agents.reviewer_agent import ReviewerAgent as _Rev

        registry.register("github_agent", GitHubAgent)
        registry.register("reviewer_agent", ReviewerAgent, system_prompt=_Rev.DEFAULT_SYSTEM_PROMPT)
        registry.register("jira_agent", JiraAgent)
        registry.register("reporter_agent", ReporterAgent)
        registry.register("orchestrator", OrchestratorAgent, system_prompt=ORCHESTRATOR_PLAN_PROMPT)


class OrchestratorAgent(BaseAgent):
    """Ince orkestrator: ajanlari baglantilarla kurar, akisi LangGraph'a devreder."""

    def __init__(self, name: str = "OrchestratorAgent", model_client: Any = None, connections: Dict[str, Any] = None):
        super().__init__(name, model_client)
        _register_defaults()

        conns = connections or {}
        github_conn = conns.get("github") or {}
        jira_conn = conns.get("jira") or {}
        llm_conn = conns.get("llm") or {}
        self._connections = {"github": github_conn, "jira": jira_conn, "llm": llm_conn}
        # Politika projesi (orn. TTA) baglanti varsayilanini ezer
        ticket_project = conns.get("ticket_project") or jira_conn.get("project_key") or ""
        gates = (conns.get("gates") or {})
        self._gates = {
            "plan_on_fail": gates.get("plan_on_fail", True),
            "plan_on_pass": gates.get("plan_on_pass", False),
        }
        tr = (conns.get("transitions") or {})
        self._transitions = {"pass": tr.get("pass") or "In Review", "fail": tr.get("fail") or "Blocked"}
        self.llm = model_client or LLMClient(connection=llm_conn)

        # Tum alt ajanlar run'in LLM baglantisini paylasir (provider secimi tek noktada)
        self.github_worker = registry.build("github_agent", connection=github_conn, model_client=self.llm)
        # Bilet anahtari: politika projesi > Jira baglantisi (cok projeli kurumlar)
        if ticket_project:
            self.github_worker.project_key = ticket_project
        elif jira_conn.get("project_key"):
            self.github_worker.project_key = jira_conn["project_key"]
        self.jira_worker = registry.build("jira_agent", connection=jira_conn, model_client=self.llm)
        self.reporter_worker = registry.build(
            "reporter_agent", system_prompt=registry.system_prompt("reporter_agent") or None,
            model_client=self.llm,
        )
        self.reviewer_worker = registry.build(
            "reviewer_agent", system_prompt=registry.system_prompt("reviewer_agent") or None,
            model_client=self.llm,
        )

    async def route_and_execute(
        self,
        user_goal: str,
        dry_run: bool = False,
        github_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        from src.agents.graph import build_graph

        logger.info("Sef Ajan: LangGraph akisi baslatiliyor (dry_run=%s)", dry_run)
        gh = github_context or {}
        workers = {
            "llm": self.llm,
            "github": self.github_worker,
            "reviewer": self.reviewer_worker,
            "jira": self.jira_worker,
            "reporter": self.reporter_worker,
            "enabled": {
                "github": registry.is_enabled("github_agent"),
                "reviewer": registry.is_enabled("reviewer_agent"),
                "jira": registry.is_enabled("jira_agent"),
                "reporter": registry.is_enabled("reporter_agent"),
            },
            "plan_prompt": registry.system_prompt("orchestrator"),
            "gates": getattr(self, "_gates", {"plan_on_fail": True, "plan_on_pass": False}),
            "transitions": getattr(self, "_transitions", {"pass": "In Review", "fail": "Blocked"}),
        }
        app = build_graph(workers)
        final = await app.ainvoke({
            "user_goal": user_goal,
            "dry_run": dry_run,
            "github_context": {
                "owner": gh.get("owner") or self.github_worker.default_owner,
                "repo": gh.get("repo", settings.GITHUB_REPO),
                "count": gh.get("count", 3),
            },
            "review_passed": True,
            "jira_planned": [],
        })
        review_passed = final.get("review_passed", True)
        return {
            "status": "success" if review_passed else "partially_blocked",
            "final_report": final.get("final_report", "Guvenlik blokaji nedeniyle surum bulteni raporu uretilmedi."),
            "commit_units": final.get("commit_units", []),
            "jira_planned": final.get("jira_planned", []),
            "dry_run": dry_run,
        }

    async def run(
        self,
        task_description: str,
        context: Dict[str, Any] = None,
        dry_run: bool = False,
        github_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        context = context or {}
        if context.get("dry_run") is True:
            dry_run = True
        return await self.route_and_execute(task_description, dry_run=dry_run, github_context=github_context)

    def get_tool_schemas(self):
        return []
