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

                # 🎯 Her commit kendi bilet ID'si + diff'iyle izole bir "birim" (unit) olarak taşınıyor
                context["commit_units"] = github_result.get("extracted_data", {}).get("commit_units", [])
                context["raw_commits"] = github_result.get("extracted_data", {}).get("raw_commits", [])

            # 2. REVIEWER ADIMI (🎯 Kalite Kapısı - artık her commit için ayrı ayrı çalışır)
            elif step == "reviewer_agent" and context.get("commit_units"):
                print(f"[Orchestrator] ⚙️ LLM Kararı: reviewer_agent tetikleniyor...")
                for unit in context["commit_units"]:
                    if not unit.get("code_changes") or not unit["code_changes"].strip():
                        unit["review_status"] = "PASSED"
                        unit["review_comment"] = "İncelenecek kod değişikliği bulunamadı."
                        continue

                    reviewer_result = await self.reviewer_worker.run(
                        "Review code quality", context={"code_changes": unit["code_changes"]}
                    )
                    unit["review_status"] = reviewer_result.get("review_status", "FAILED")
                    unit["review_comment"] = reviewer_result.get("review_comment", "")

                    if unit["review_status"] == "FAILED":
                        logger.warning(
                            f"🚨 Commit {unit.get('short_sha')} içinde kritik kod kalitesi/güvenlik "
                            f"riski saptandı! Sadece bu commit'e ait bilet(ler) kilitlenecek."
                        )

                # Genel rapor/özet için: en az bir commit FAILED ise akışı "kısmen bloklu" say
                if any(u.get("review_status") == "FAILED" for u in context["commit_units"]):
                    review_passed = False

            # 3. JIRA ADIMI (🎯 Dynamic Gatekeeping - artık her commit kendi review sonucunu taşıyor)
            elif step == "jira_agent" and context.get("commit_units"):
                any_ticket_processed = False
                for unit in context["commit_units"]:
                    if not unit.get("jira_ids"):
                        continue
                    any_ticket_processed = True

                    unit_review_passed = unit.get("review_status", "PASSED") != "FAILED"
                    print(
                        f"[Orchestrator] ⚙️ LLM Kararı: jira_agent tetikleniyor "
                        f"(commit {unit.get('short_sha')} -> {unit['jira_ids']})..."
                    )

                    if not unit_review_passed:
                        logger.info(
                            f"❌ Commit {unit.get('short_sha')} onay almadığı için ilgili Jira "
                            f"bilet(ler)ine blokaj verisi ve yorumu hazırlanıyor."
                        )
                        jira_context = {
                            "jira_ids": unit["jira_ids"],
                            "action": "both",
                            "code_changes": f"⚠️ [GÜVENLİK/KALİTE BLOKAJI]\n{unit.get('review_comment', '')}",
                            "review_passed": False
                        }
                    else:
                        jira_context = {
                            "jira_ids": unit["jira_ids"],
                            "action": "both",
                            "code_changes": unit.get("code_changes", ""),
                            "review_passed": True
                        }

                    await self.jira_worker.run("Update", context=jira_context)

                if not any_ticket_processed:
                    logger.info(
                        "ℹ️ jira_agent planlanmıştı ancak hiçbir commit'te Jira bilet ID'si "
                        "bulunamadığı için bu adım atlandı (regex ve LLM fallback ikisi de sonuçsuz kaldı)."
                    )

            elif step == "jira_agent" and not context.get("commit_units"):
                logger.info(
                    "ℹ️ jira_agent planlanmıştı ancak hiçbir Jira bilet ID'si bulunamadığı "
                    "için bu adım atlandı (regex ve LLM fallback ikisi de sonuçsuz kaldı)."
                )

            # 4. REPORTER ADIMI (sadece review'dan geçen commit'leri raporlar)
            elif step == "reporter_agent" and context.get("raw_commits"):
                print(f"[Orchestrator] ⚙️ LLM Kararı: reporter_agent tetikleniyor...")

                if context.get("commit_units"):
                    blocked_shas = {
                        u["sha"] for u in context["commit_units"] if u.get("review_status") == "FAILED"
                    }
                    reportable_commits = [c for c in context["raw_commits"] if c.get("sha") not in blocked_shas]
                else:
                    reportable_commits = context["raw_commits"]

                if not reportable_commits:
                    logger.info("ℹ️ Tüm commit'ler bloklandığı için raporlanacak onaylı değişiklik yok.")
                    context["final_report"] = "Tüm değişiklikler güvenlik/kalite blokajı nedeniyle raporlanamadı."
                else:
                    reporter_context = {"raw_commits": reportable_commits}
                    reporter_result = await self.reporter_worker.run("Report", context=reporter_context)
                    context["final_report"] = reporter_result.get("generated_report")

        return {
            "status": "success" if review_passed else "partially_blocked",
            "final_report": context.get("final_report", "Güvenlik blokajı nedeniyle sürüm bülteni raporu üretilmedi.")
        }

    async def run(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        return await self.route_and_execute(task_description)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []