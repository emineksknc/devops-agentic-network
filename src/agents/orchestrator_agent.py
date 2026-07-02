import logging
import json
from typing import List, Dict, Any
from src.core.base_agent import BaseAgent
from src.core.llm_client import LLMClient
from src.agents.github_agent import GitHubAgent
from src.agents.jira_agent import JiraAgent
from src.agents.reporter_agent import ReporterAgent
from src.agents.reviewer_agent import ReviewerAgent  # 🎯 1. Yeni ajanı import ediyoruz
from src.config.settings import settings

logger = logging.getLogger("OrchestratorAgent")

class OrchestratorAgent(BaseAgent):
    def __init__(self, name: str = "OrchestratorAgent", model_client: Any = None):
        super().__init__(name, model_client)
        self.llm = model_client or LLMClient()
        
        self.github_worker = GitHubAgent()
        self.jira_worker = JiraAgent()
        self.reporter_worker = ReporterAgent()
        self.reviewer_worker = ReviewerAgent()  # 🎯 2. Ajanı ayağa kaldırıyoruz

    async def route_and_execute(self, user_goal: str) -> Dict[str, Any]:
        logger.info("🎼 Şef Ajan (Orchestrator) otonom iş planı hazırlıyor...")

        system_prompt = (
            "Sen bir DevOps Orkestra Şefisin. Elinde şu 4 alt ajan (araç) var:\n"
            "1. 'github_agent': Canlı depodan son commitleri okur.\n"
            "2. 'reviewer_agent': Kod kalitesi ve güvenlik analizini yapıp PASSED/FAILED raporlar.\n"
            "3. 'jira_agent': Bulunan biletleri Jira'da günceller.\n"
            "4. 'reporter_agent': Commitlerden Türkçe sürüm raporu hazırlar.\n\n"
            "Kullanıcının hedefine bakarak, hangi sırayla hangi ajanları çalıştırman gerektiğini planla.\n"
            "Yönlendirme Kuralları: Kodları incelemeden kalite analizi veya jira güncellemesi yapamazsın.\n"
            "Yanıtını SADECE ve SADECE şu JSON formatında dön, başka hiçbir açıklama yazma:\n"
            "{\n"
            "  \"plan\": [\"ajan_adi_1\", \"ajan_adi_2\"],\n"
            "  \"reason\": \"Bu planı yapma nedenin\"\n"
            "}"
        )

        llm_plan_raw = await self.llm.generate_response(system_prompt, f"Hedef: {user_goal}")
        
        print("\n==================================================")
        print("🧠 OLLAMA TARAFINDAN OLUŞTURULAN OTONOM İŞ PLANI:")
        print("==================================================")
        print(llm_plan_raw)
        print("==================================================\n")

        context = {}
        try:
            plan_json = json.loads(llm_plan_raw.replace("```json", "").replace("```", "").strip())
            execution_steps = plan_json.get("plan", [])
            logger.info(f"✅ LLM planı başarıyla parse edildi. Adımlar: {execution_steps}")
        except Exception as e:
            logger.warning(
                f"⚠️ LLM geçerli bir JSON dönmedi! Hata: {e}. Fallback akışı aktif ediliyor."
            )
            execution_steps = ["github_agent", "reviewer_agent", "jira_agent", "reporter_agent"]

        # Kalite kontrol durumunu izlemek için bir bayrak tutuyoruz
        review_passed = True
        review_comment = ""

        for step in execution_steps:
            # 1. GITHUB ADIMI
            if step == "github_agent":
                print(f"[Orchestrator] ⚙️ LLM Kararı: github_agent tetikleniyor...")
                github_context = {"owner": settings.GITHUB_OWNER, "repo": settings.GITHUB_REPO, "count": 3}
                github_result = await self.github_worker.run("Scan", context=github_context)
                
                context["raw_commits"] = github_result.get("extracted_data", {}).get("raw_commits", [])
                context["jira_ids"] = github_result.get("extracted_data", {}).get("jira_ids_found", [])
                context["code_changes"] = github_result.get("extracted_data", {}).get("code_changes", "")
                
            # 2. REVIEWER ADIMI (🎯 Kalite Kapısı)
            elif step == "reviewer_agent" and context.get("code_changes"):
                print(f"[Orchestrator] ⚙️ LLM Kararı: reviewer_agent tetikleniyor...")
                reviewer_result = await self.reviewer_worker.run("Review code quality", context=context)
                
                status = reviewer_result.get("review_status", "PASSED")
                review_comment = reviewer_result.get("review_comment", "")
                
                if status == "FAILED":
                    logger.warning("🚨 Kritik kod kalitesi veya güvenlik riski saptandı! İş akışı kilitlenecek.")
                    review_passed = False
                
            # 3. JIRA ADIMI (🎯 Dynamic Gatekeeping Entegrasyonu)
            elif step == "jira_agent" and context.get("jira_ids"):
                print(f"[Orchestrator] ⚙️ LLM Kararı: jira_agent tetikleniyor...")
                
                if not review_passed:
                    logger.info("❌ Kod onay almadığı için Jira bileceğine blokaj verisi ve yorumu hazırlanıyor.")
                    jira_context = {
                        "jira_ids": context["jira_ids"], 
                        "action": "both",
                        "code_changes": f"⚠️ [GÜVENLİK/KALİTE BLOKAJI]\n{review_comment}",
                        "review_passed": False  # 🎯 JiraAgent'a kodun kaldığını bildiriyoruz!
                    }
                else:
                    jira_context = {
                        "jira_ids": context["jira_ids"], 
                        "action": "both",
                        "code_changes": context.get("code_changes", ""),
                        "review_passed": True   # 🎯 JiraAgent'a kodun geçtiğini bildiriyoruz!
                    }
                
                await self.jira_worker.run("Update", context=jira_context)
                
            # 4. REPORTER ADIMI
            elif step == "reporter_agent" and context.get("raw_commits") and review_passed:
                print(f"[Orchestrator] ⚙️ LLM Kararı: reporter_agent tetikleniyor...")
                reporter_context = {"raw_commits": context["raw_commits"]}
                reporter_result = await self.reporter_worker.run("Report", context=reporter_context)
                context["final_report"] = reporter_result.get("generated_report")

        return {
            "status": "success" if review_passed else "blocked",
            "final_report": context.get("final_report", "Güvenlik blokajı nedeniyle sürüm bülteni raporu üretilmedi.")
        }

    async def run(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        return await self.route_and_execute(task_description)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []