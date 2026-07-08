import logging
from typing import List, Dict, Any
import httpx
from src.core.base_agent import BaseAgent
from src.config.settings import settings
from src.core.llm_client import LLMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JiraAgent")

class JiraAgent(BaseAgent):
    def __init__(self, name: str = "JiraAgent", model_client: Any = None):
        super().__init__(name, model_client)
        self.llm = model_client or LLMClient()
        self.register_tool("add_comment_to_ticket", self.add_comment_to_ticket)
        self.register_tool("transition_ticket_status", self.transition_ticket_status)

    def _get_auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth(username=settings.JIRA_USER_EMAIL, password=settings.JIRA_API_TOKEN)

    def _base_url(self) -> str:
        # settings.JIRA_DOMAIN sonunda "/" olsa bile çift slash oluşmasını engeller
        return settings.JIRA_DOMAIN.rstrip("/")

    async def ticket_exists(self, ticket_id: str) -> bool:
        """
        🛡️ GUARDRAIL: İşlem yapmadan önce biletin gerçekten Jira'da var olduğunu doğrular.
        Bu, GitHubAgent'ın LLM fallback yolunun (semantik bilet çıkarımı) olası bir
        halüsinasyon sonucu var olmayan bir bilet numarası üretmesine karşı korur.
        """
        url = f"{self._base_url()}/rest/api/3/issue/{ticket_id}?fields=key"
        headers = {"Accept": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, auth=self._get_auth())
                if response.status_code == 200:
                    return True
                elif response.status_code == 404:
                    logger.info(f"ℹ️ {ticket_id} Jira'da bulunamadı (404) - gerçekten mevcut değil.")
                    return False
                else:
                    logger.warning(
                        f"⚠️ {ticket_id} doğrulanırken beklenmeyen durum kodu: "
                        f"{response.status_code} - {response.text[:200]}"
                    )
                    return False
        except Exception as e:
            # 🔍 Teşhis için tam hata tipini ve mesajını logluyoruz (str(e) bazen boş kalabiliyor)
            logger.error(
                f"❌ Jira Bağlantı Hatası (Bilet Doğrulama) [{type(e).__name__}]: {repr(e)}"
            )
            # Bağlantı hatasında da güvenli tarafta kalıyoruz: bilet yok say, işlem yapma
            return False

    async def add_comment_to_ticket(self, ticket_id: str, comment_text: str) -> bool:
        url = f"{self._base_url()}/rest/api/3/issue/{ticket_id}/comment"
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
        url = f"{self._base_url()}/rest/api/3/issue/{ticket_id}/transitions"
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
        
        # Orchestrator'dan gelen kalite/güvenlik durumunu okuyoruz (Varsayılan: True)
        review_passed = context.get("review_passed", True) 
        
        # 🎯 GitHubAgent'tan gelen diff verisi
        code_changes = (
            context.get("code_changes") or 
            context.get("patch") or 
            context.get("diff") or 
            ""
        )
        
        if isinstance(code_changes, list) or isinstance(code_changes, dict):
            code_changes = str(code_changes)

        # 🤖 Otonom Kod Yorumu Analizi (LLM ile)
        ai_comment_summary = ""
        if code_changes and code_changes.strip() and action in ["comment", "both"]:
            try:
                logger.info(f"🧠 JiraAgent: Lokal LLM (Ollama) ile kod diff analizi yapılıyor...")
                
                # Eğer kod denetimden kaldıysa promptu ona göre şekillendiriyoruz
                if not review_passed:
                    comment_prompt = (
                        "Sen otonom bir DevOps Yapay Zeka Asistanısın.\n"
                        "Sana güvenlik veya kalite denetiminden KALMIŞ tehlikeli bir kod değişikliği (diff) verilecek.\n"
                        "Görevin, bu kodun neden başarısız olduğunu ve ne tür riskler barındırdığını "
                        "maksimum 2-3 cümlelik, kurumsal, profesyonel ve Türkçe bir dille özetlemektir.\n"
                        "Doğrudan teknik özeti dön, 'İşte hata:' gibi ifadeler kullanma.\n\n"
                        f"Başarısız Olan Kod Değişiklikleri:\n{code_changes}"
                    )
                else:
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
            # 🛡️ GUARDRAIL: İşlem yapmadan önce biletin gerçekten var olduğunu doğrula.
            # LLM fallback yolu (semantik bilet çıkarımı) yanlışlıkla var olmayan bir
            # bilet numarası üretmiş olabilir; bu durumda sessizce atla, hata verip
            # tüm akışı çökertme.
            if not await self.ticket_exists(ticket_id):
                logger.warning(
                    f"⚠️ {ticket_id} Jira'da bulunamadı (muhtemelen LLM'in ürettiği "
                    f"geçersiz bir referans). Bu bilet atlanıyor, işlem yapılmayacak."
                )
                results[ticket_id] = {"comment": False, "transition": False, "skipped_reason": "ticket_not_found"}
                continue

            results[ticket_id] = {"comment": False, "transition": False}
            if action in ["comment", "both"]:
                if ai_comment_summary and ai_comment_summary.strip():
                    # Başlığımızı duruma göre dinamik yapıyoruz
                    report_title = "🚨 [DAN - Otonom Kod KALİTE/GÜVENLİK BLOKAJI]" if not review_passed else "🤖 [DAN - Otonom Kod Analiz Raporu]"
                    msg = (
                        f"{report_title}\n\n"
                        f"⚙️ Analiz Eden Ajan: {self.name}\n"
                        f"📝 Teknik Analiz/Risk Detayı:\n{ai_comment_summary}\n\n"
                        f"{'❌ İş akışı güvenlik/kalite standartları gereği kilitlendi.' if not review_passed else '🚀 Otomatik kod doğrulama ve pipeline adımları başarıyla tamamlandı.'}"
                    )
                else:
                    msg = (
                        "🤖 [🤖 DevOps Agentic Network - Otonom İşlem Raporu]\n\n"
                        f"⚙️ İşlem Yapan Ajan: {self.name}\n"
                        f"📦 Tetikleyici Eylem: GitHub Canlı Commit Analizi\n"
                        f"📝 Durum: Bu biletle ilişkili geliştirici kodları başarıyla doğrulandı.\n"
                    )
                results[ticket_id]["comment"] = await self.add_comment_to_ticket(ticket_id, msg)
                
            if action in ["transition", "both"]:
                # 🎯 DİNAMİK WORKFLOW: Kalite kontrol geçildiyse 'In Review', kaldıysa 'Blocked' aşamasına çekiyoruz
                target_status = "In Review" if review_passed else "Blocked"
                results[ticket_id]["transition"] = await self.transition_ticket_status(ticket_id, target_status)

        return {
            "agent": self.name,
            "status": "success",
            "processed_tickets": len(jira_ids),
            "details": results
        } 
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []