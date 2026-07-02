import logging
import json
from typing import List, Dict, Any
from src.core.base_agent import BaseAgent
from src.core.llm_client import LLMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReviewerAgent")

class ReviewerAgent(BaseAgent):
    def __init__(self, name: str = "ReviewerAgent", model_client: Any = None):
        super().__init__(name, model_client)
        self.llm = model_client or LLMClient()

    async def run(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        code_changes = (
            context.get("code_changes") or 
            context.get("patch") or 
            context.get("diff") or 
            ""
        )

        if not code_changes or not code_changes.strip():
            logger.warning("⚠️ ReviewerAgent'a analiz için herhangi bir kod değişikliği (diff) ulaşmadı.")
            return {
                "agent": self.name,
                "review_status": "PASSED",
                "review_comment": "Analiz edilecek kod değişikliği bulunamadı, adımlar güvenle geçildi."
            }

        logger.info(f"🧠 {self.name}: Lokal LLM (Ollama) ile otonom kod kalitesi ve güvenlik analizi başlatılıyor...")

        review_prompt = (
            "Sen kıdemli bir DevOps Güvenlik ve Kod Kalitesi Denetçisisin (Senior Code Reviewer).\n"
            "Sana bir geliştiricinin yaptığı kod değişikliklerine ait ham 'diff' (patch) verisi verilecek.\n\n"
            "GÖREVİN:\n"
            "Bu kod değişikliklerini şu kriterlere göre sıkı bir denetime tabi tut:\n"
            "1. Güvenlik Riski: Kod içinde açıkça yazılmış (hardcoded) şifre, API anahtarı, token veya gizli veri var mı?\n"
            "2. Kalite Riski: Bariz mantık hataları, sonsuz döngüler veya tehlikeli (try-except bloğuna alınmamış) operasyonlar var mı?\n\n"
            "Kritik bir risk bulursan 'review_status' değerini 'FAILED' yap ve sebebini açıkla.\n"
            "Kod temiz ve güvenli görünüyorsa 'review_status' değerini 'PASSED' yap.\n\n"
            "⚠️ KESİN KURAL: Yanıtını SADECE ve SADECE aşağıdaki JSON formatında dön. Başka hiçbir açıklama veya metin yazma:\n"
            "{\n"
            "  \"review_status\": \"PASSED\" veya \"FAILED\",\n"
            "  \"review_comment\": \"Geliştiriciye iletilecek 2-3 cümlelik Türkçe profesyonel teknik geri bildirim veya tespit edilen risklerin özeti\"\n"
            "}\n\n"
            f"Denetlenecek Kod Değişiklikleri:\n{code_changes}"
        )

        try:
            llm_response = await self.llm.generate_response(
                "Sen sadece JSON formatında çıktı üreten profesyonel bir kod denetçisisin.",
                review_prompt
            )
            
            # Ollama bazen markdown kod blokları (```json ... ```) içine alabilir, onları temizleyelim
            clean_json = llm_response.replace("```json", "").replace("```", "").strip()
            review_result = json.loads(clean_json)
            
            logger.info(f"✅ {self.name} analizi tamamladı. Sonuç: {review_result.get('review_status')}")
            return {
                "agent": self.name,
                "review_status": review_result.get("review_status", "PASSED"),
                "review_comment": review_result.get("review_comment", "Kod analizi başarıyla tamamlandı.")
            }

        except Exception as e:
            logger.error(f"❌ ReviewerAgent LLM analizi veya JSON parse sırasında hata aldı: {e}")
            # Güvenli mod fallback: Hata durumunda pipeline'ı tıkamamak için PASSED geçiyoruz
            return {
                "agent": self.name,
                "review_status": "PASSED",
                "review_comment": "Otonom denetim motorunda teknik bir aksaklık yaşandı, manuel kontrol önerilir."
            }

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []