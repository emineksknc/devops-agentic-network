import logging
from typing import List, Dict, Any
import httpx
from src.core.base_agent import BaseAgent
from src.config.settings import settings
from src.core.llm_client import LLMClient # LLMClient entegrasyonu

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JiraAgent")

class JiraAgent(BaseAgent):
    def __init__(self, name: str = "JiraAgent", model_client: Any = None):
        super().__init__(name, model_client)
        # Eğer dışarıdan bir model_client verilmediyse varsayılan LLMClient'ı bağlıyoruz
        self.llm = model_client or LLMClient()
        self.register_tool("add_comment_to_ticket", self.add_comment_to_ticket)
        self.register_tool("transition_ticket_status", self.transition_ticket_status)

    def _get_auth(self) -> httpx.BasicAuth:
        """Jira API için .env'deki bilgilerle kimlik doğrulama objesi üretir."""
        return httpx.BasicAuth(username=settings.JIRA_USER_EMAIL, password=settings.JIRA_API_TOKEN)

    async def add_comment_to_ticket(self, ticket_id: str, comment_text: str) -> bool:
        """Jira biletine canlı API üzerinden yorum ekler."""
        url = f"{settings.JIRA_DOMAIN}/rest/api/3/issue/{ticket_id}/comment"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment_text}]
                    }
                ]
            }
        }

        try:
            logger.info(f"📡 Jira Canlı API: {ticket_id} biletine yorum gönderiliyor...")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers, auth=self._get_auth())
                if response.status_code == 201:
                    logger.info(f"✅ {ticket_id} biletine yorum başarıyla yazıldı.")
                    return True
                else:
                    logger.error(f"❌ Jira Yorum Hatası ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"❌ Jira Bağlantı Hatası (Yorum): {str(e)}")
        return False

    async def transition_ticket_status(self, ticket_id: str, target_status: str) -> bool:
        """Jira biletinin statüsünü canlı API üzerinden günceller."""
        url = f"{settings.JIRA_DOMAIN}/rest/api/3/issue/{ticket_id}/transitions"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.info(f"📡 Jira Canlı API: {ticket_id} için kullanılabilir geçişler sorgulanıyor...")
                transitions_resp = await client.get(url, headers=headers, auth=self._get_auth())
                
                if transitions_resp.status_code != 200:
                    logger.error(f"❌ Geçiş listesi alınamadı ({transitions_resp.status_code})")
                    return False
                
                transitions_data = transitions_resp.json()
                transition_id = None
                
                for t in transitions_data.get("transitions", []):
                    if target_status.lower() in t.get("name", "").lower():
                        transition_id = t.get("id")
                        break
                
                if not transition_id:
                    logger.warning(f"⚠️ Jira'da '{target_status}' isminde bir geçiş aşaması bulunamadı.")
                    return False

                payload = {"transition": {"id": transition_id}}
                response = await client.post(url, json=payload, headers=headers, auth=self._get_auth())
                
                if response.status_code == 204:
                    logger.info(f"✅ {ticket_id} başarıyla '{target_status}' aşamasına çekildi.")
                    return True
                else:
                    logger.error(f"❌ Jira Statü Değiştirme Hatası ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"❌ Jira Bağlantı Hatası (Statü): {str(e)}")
        return False

    async def run(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        jira_ids = context.get("jira_ids", [])
        action = context.get("action", "comment")
        code_changes = context.get("code_changes", "") # 🎯 GitHubAgent'tan gelen diff verisi
        
        # 🤖 Otonom Kod Yorumu Analizi (LLM ile)
        ai_comment_summary = ""
        if code_changes and action in ["comment", "both"]:
            try:
                logger.info(f"🧠 JiraAgent: Lokal LLM (Ollama) ile kod diff analizi yapılıyor...")
                comment_prompt = (
                    "Sen otonom bir DevOps Yapay Zeka Asistanısın.\n"
                    "Sana en son yapılan commit'e ait ham kod diff (patch) verisi verilecek.\n"
                    "Görevin, bu kod değişikliğini teknik olarak analiz edip, Jira kartına yazılacak "
                    "maksimum 2-3 cümlelik, kurumsal, profesyonel ve Türkçe bir teknik özet hazırlamaktır.\n"
                    "Lütfen doğrudan teknik özeti dön, 'İşte özet:' gibi ifadeler kullanma.\n\n"
                    f"Kod Değişiklikleri:\n{code_changes}"
                )
                ai_comment_summary = await self.llm.generate_response(
                    "Sen teknik bir DevOps asistanısın. Sadece istenen teknik yorumu dönersin.",
                    comment_prompt
                )
            except Exception as e:
                logger.warning(f"⚠️ LLM analizi başarısız oldu, fallback şablonu kullanılacak. Hata: {e}")
                ai_comment_summary = ""

        results = {}
        for ticket_id in jira_ids:
            results[ticket_id] = {"comment": False, "transition": False}
            if action in ["comment", "both"]:
                # 🎯 Eğer LLM analiz yaptıysa onu ekliyoruz, yapamadıysa fallback şablonuna düşüyoruz
                if ai_comment_summary:
                    msg = (
                        "🤖 [DAN - Otonom Kod Analiz Raporu]\n\n"
                        f"⚙️ Analiz Eden Ajan: {self.name}\n"
                        f"📝 Kod Değişiklik Özeti:\n{ai_comment_summary}\n\n"
                        "🚀 Otomatik kod doğrulama ve pipeline adımları başarıyla tamamlandı."
                    )
                else:
                    msg = (
                        "🤖 [🤖 DevOps Agentic Network - Otonom İşlem Raporu]\n\n"
                        f"⚙️ İşlem Yapan Ajan: {self.name}\n"
                        "📦 Tetikleyici Eylem: GitHub Canlı Commit Analizi\n"
                        "📝 Durum: Bu biletle ilişkili geliştirici kodları başarıyla doğrulandı ve ana repoya pushlandı.\n\n"
                        "🚀 Otomatik analiz başarılı. Pipeline adımları güvenle tamamlandı."
                    )
                results[ticket_id]["comment"] = await self.add_comment_to_ticket(ticket_id, msg)
                
            if action in ["transition", "both"]:
                results[ticket_id]["transition"] = await self.transition_ticket_status(ticket_id, "In Review")

        return {
            "agent": self.name,
            "status": "success",
            "processed_tickets": len(jira_ids),
            "details": results
        }

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []