# import logging
# from typing import List, Dict, Any
# from src.core.base_agent import BaseAgent
# from src.core.llm_client import LLMClient
# from src.agents.github_agent import GitHubAgent
# from src.agents.jira_agent import JiraAgent
# from src.agents.reporter_agent import ReporterAgent
# from src.config.settings import settings

# logger = logging.getLogger("OrchestratorAgent")

# class OrchestratorAgent(BaseAgent):
#     """
#     Tüm Multi-Agent sistemini yöneten, alt ajanları birer 'Araç (Tool)'
#     olarak koşturan ve iş akışına dinamik karar veren Şef Ajan.
#     """
#     def __init__(self, name: str = "OrchestratorAgent", model_client: Any = None):
#         super().__init__(name, model_client)
#         self.llm = model_client or LLMClient()
        
#         # Alt ajanları işçi (worker) olarak tanımlıyoruz
#         self.github_worker = GitHubAgent()
#         self.jira_worker = JiraAgent()
#         self.reporter_worker = ReporterAgent()

#     async def route_and_execute(self, user_goal: str) -> Dict[str, Any]:
#         """
#         Kullanıcının hedefini alır, LLM ile analiz eder ve otonom bir 
#         plan doğrultusunda alt ajanları sırayla tetikler.
#         """
#         logger.info("🎼 Şef Ajan (Orchestrator) otonom iş planı hazırlıyor...")
        
#         # Adım 1: GitHub Tarama Aşaması
#         # Şef karar veriyor: Önce commit'leri çekmeliyiz.
#         github_context = {
#             "owner": settings.GITHUB_OWNER,
#             "repo": settings.GITHUB_REPO,
#             "count": 3
#         }
#         print(f"\n[Orchestrator] 🤖 -> {self.github_worker.name} tetikleniyor...")
#         github_result = await self.github_worker.run("Scan repository", context=github_context)
        
#         extracted_ids = github_result.get("extracted_data", {}).get("jira_ids_found", [])
#         raw_commits = github_result.get("extracted_data", {}).get("raw_commits", [])
        
#         if not extracted_ids:
#             logger.info("⚠️ Yeni bir bilet veya commit saptanmadı, iş akışı sonlandırılıyor.")
#             return {"status": "no_changes_detected", "message": "Repo üzerinde yeni bir işlem bulunamadı."}

#         # Adım 2: Jira Canlı Pano Güncelleme Aşaması
#         # Şef veriyi inceliyor ve bir sonraki adıma karar veriyor.
#         print(f"[Orchestrator] 🤖 -> {self.jira_worker.name} tetikleniyor...")
#         jira_context = {"jira_ids": extracted_ids, "action": "both"}
#         await self.jira_worker.run("Update biletleri", context=jira_context)

#         # Adım 3: Yapay Zeka Rapor Üretim Aşaması
#         print(f"[Orchestrator] 🤖 -> {self.reporter_worker.name} tetikleniyor...")
#         reporter_context = {"raw_commits": raw_commits}
#         reporter_result = await self.reporter_worker.run("Rapor oluştur", context=reporter_context)
        
#         return {
#             "status": "success",
#             "orchestrator_summary": "Tüm alt ajanlar başarıyla yönetildi ve pipeline tamamlandı.",
#             "final_report": reporter_result.get("generated_report")
#         }

#     async def run(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
#         return await self.route_and_execute(task_description)

#     def get_tool_schemas(self) -> List[Dict[str, Any]]:
#         return [] 




import logging
import json
from typing import List, Dict, Any
from src.core.base_agent import BaseAgent
from src.core.llm_client import LLMClient
from src.agents.github_agent import GitHubAgent
from src.agents.jira_agent import JiraAgent
from src.agents.reporter_agent import ReporterAgent
from src.config.settings import settings

logger = logging.getLogger("OrchestratorAgent")

class OrchestratorAgent(BaseAgent):
    def __init__(self, name: str = "OrchestratorAgent", model_client: Any = None):
        super().__init__(name, model_client)
        self.llm = model_client or LLMClient()
        
        self.github_worker = GitHubAgent()
        self.jira_worker = JiraAgent()
        self.reporter_worker = ReporterAgent()

    async def route_and_execute(self, user_goal: str) -> Dict[str, Any]:
        logger.info("🎼 Şef Ajan (Orchestrator) otonom iş planı hazırlıyor...")

        # 🎯 AJANTİK YAPI BURADA BAŞLIYOR: 
        # Modeli bir "Router" olarak konumlandırıyoruz. Elindeki araçları listeliyoruz.
        system_prompt = (
            "Sen bir DevOps Orkestra Şefisin. Elinde şu 3 alt ajan (araç) var:\n"
            "1. 'github_agent': Canlı depodan son commitleri okur.\n"
            "2. 'jira_agent': Bulunan biletleri Jira'da günceller.\n"
            "3. 'reporter_agent': Commitlerden Türkçe sürüm raporu hazırlar.\n\n"
            "Kullanıcının hedefine bakarak, hangi sırayla hangi ajanları çalıştırman gerektiğini planla.\n"
            "Yanıtını SADECE ve SADECE şu JSON formatında dön, başka hiçbir açıklama yazma:\n"
            "{\n"
            "  \"plan\": [\"ajan_adi_1\", \"ajan_adi_2\"],\n"
            "  \"reason\": \"Bu planı yapma nedenin\"\n"
            "}"
        )

        # Ollama'dan planı istiyoruz
        llm_plan_raw = await self.llm.generate_response(system_prompt, f"Hedef: {user_goal}")
        
        # Yapay zekanın yaptığı planı loglarda görebilmek için ekrana basıyoruz
        print("\n==================================================")
        print("🧠 OLLAMA TARAFINDAN OLUŞTURULAN OTONOM İŞ PLANI:")
        print("==================================================")
        print(llm_plan_raw)
        print("==================================================\n")

        # Planı koda döküyoruz (Dinamik Execution)
       # Planı koda döküyoruz (Dinamik Execution)
        context = {}
        try:
            plan_json = json.loads(llm_plan_raw)
            execution_steps = plan_json.get("plan", [])
            # Başarılı geçildiğini loglamak istersen opsiyonel:
            logger.info(f"✅ LLM planı başarıyla parse edildi. Adımlar: {execution_steps}")
            
        except Exception as e:
            # 🎯 BURAYA DÜŞTÜĞÜNÜ GÖSTEREN LOG:
            logger.warning(
                f"⚠️ LLM geçerli bir JSON dönmedi! Hata: {e}. "
                f"Güvenli mod (Fallback) aktif ediliyor, varsayılan akış koşturulacak."
            )
            # Fallback mantığı
            execution_steps = ["github_agent", "jira_agent", "reporter_agent"]

        # 🤖 Şef, LLM'den gelen listeyi dinamik olarak dönüyor:
        for step in execution_steps:
            if step == "github_agent":
                print(f"[Orchestrator] ⚙️ LLM Kararı: github_agent tetikleniyor...")
                github_context = {"owner": settings.GITHUB_OWNER, "repo": settings.GITHUB_REPO, "count": 3}
                github_result = await self.github_worker.run("Scan", context=github_context)
                context["raw_commits"] = github_result.get("extracted_data", {}).get("raw_commits", [])
                context["jira_ids"] = github_result.get("extracted_data", {}).get("jira_ids_found", [])
                
            elif step == "jira_agent" and context.get("jira_ids"):
                print(f"[Orchestrator] ⚙️ LLM Kararı: jira_agent tetikleniyor...")
                jira_context = {"jira_ids": context["jira_ids"], "action": "both"}
                await self.jira_worker.run("Update", context=jira_context)
                
            elif step == "reporter_agent" and context.get("raw_commits"):
                print(f"[Orchestrator] ⚙️ LLM Kararı: reporter_agent tetikleniyor...")
                reporter_context = {"raw_commits": context["raw_commits"]}
                reporter_result = await self.reporter_worker.run("Report", context=reporter_context)
                context["final_report"] = reporter_result.get("generated_report")

        return {
            "status": "success",
            "final_report": context.get("final_report", "Rapor üretilemedi.")
        }

    async def run(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        return await self.route_and_execute(task_description)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []