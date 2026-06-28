import logging
from typing import List, Dict, Any
from src.core.base_agent import BaseAgent
from src.core.llm_client import LLMClient

logger = logging.getLogger("ReporterAgent")

class ReporterAgent(BaseAgent):
    """
    GitHub commit geçmişini ve operasyon loglarını okuyarak
    Lokal LLM yardımıyla yönetici dostu Markdown bültenleri hazırlayan ajan.
    """
    def __init__(self, name: str = "ReporterAgent", model_client: Any = None):
        super().__init__(name, model_client)
        # Eğer dışarıdan bir model client verilmediyse kendi lokal istemcisini ayağa kaldırır
        self.llm = model_client or LLMClient()
        self.register_tool("generate_markdown_report", self.generate_markdown_report)

    async def generate_markdown_report(self, raw_commits: List[Dict[str, Any]]) -> str:
        """
        Ham commit verilerini toplayıp Ollama'ya anlamlı bir özet ürettirir.
        """
        if not raw_commits:
            return "### 📅 Haftalık Geliştirme Raporu\n\n⚠️ Bu dönemde analiz edilecek yeni bir kod değişikliği saptanmadı."

        # Modeli beslemek için ham commit mesajlarını bir metin bloğu haline getiriyoruz
        commit_logs = ""
        for c in raw_commits:
            commit_logs += f"- SHA: {c.get('sha')}, Yazar: {c.get('author')}, Mesaj: {c.get('message')}\n"

        system_prompt = (
            "Sen kıdemli bir Teknik Ürün Yöneticisisin (Technical Product Manager). "
            "Sana mühendislerden gelen ham GitHub commit mesajları verilecek. "
            "Görevin, bu ham teknik dili tamamen Türkçe, kurumsal, şık ve iş odaklı (business-value) "
            "bir Markdown Sürüm Bültenine (Release Notes) dönüştürmektir. "
            "Teknik terimleri (Örn: null pointer, hotfix, connection leak) yöneticilerin anlayacağı "
            "kararlılık, güvenlik ve performans kazanımları olarak ifade et. Gereksiz SHA kodlarını raporda sergileme."
        )

        user_prompt = (
            f"Lütfen aşağıdaki ham commit geçmişini profesyonel bir bülten haline getir:\n\n{commit_logs}"
        )

        logger.info("🧠 Lokal LLM (Ollama) teknik bülteni oluşturmak için tetikleniyor...")
        report = await self.llm.generate_response(system_prompt, user_prompt)
        return report

    async def run(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        # GitHubAgent'ın bir önceki adımda ürettiği ham commit listesini context'ten yakalıyoruz
        raw_commits = context.get("raw_commits", [])
        
        report_output = await self.generate_markdown_report(raw_commits)
        
        return {
            "agent": self.name,
            "status": "success",
            "generated_report": report_output
        }

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []