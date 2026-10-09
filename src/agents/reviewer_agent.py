import re
import logging
import json
from typing import List, Dict, Any
from src.core.base_agent import BaseAgent
from src.core.llm_client import LLMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReviewerAgent")

class ReviewerAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT = "Sen sadece JSON formatında çıktı üreten profesyonel bir kod denetçisisin."

    def __init__(self, name: str = "ReviewerAgent", model_client: Any = None, system_prompt: str = None, **kwargs):
        super().__init__(name, model_client)
        self.llm = model_client or LLMClient()
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT

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
            "Sana bir geliştiricinin yaptığı kod değişikliklerine ait ham 'diff' (patch) verisi verilecek.\n"
            "Diff'teki her dosya bloğu '--- Dosya: <dosya_adı> ---' başlığıyla ayrılmıştır.\n\n"
            "GÖREVİN:\n"
            "Bu kod değişikliklerini şu kriterlere göre sıkı bir denetime tabi tut:\n"
            "1. Güvenlik Riski: Kod içinde açıkça yazılmış (hardcoded) şifre, API anahtarı, token veya gizli veri var mı?\n"
            "2. Kalite Riski: Bariz mantık hataları, sonsuz döngüler veya tehlikeli (try-except bloğuna alınmamış) operasyonlar var mı?\n\n"
            "KANIT KURALI (cok onemli): 'FAILED' SADECE diff'te gordugun SOMUT bir satira dayanabilir. "
            "Suphe, genel ihtiyat veya 'emin olamadim' FAILED sebebi DEGILDIR; o durumda PASSED ver. "
            "Ornek FAILED gerekcesi: \"+password = '12345' satirinda acik sifre var.\" "
            "Ornek PASSED gerekcesi: \"Degisiklikler yalnizca yapi/config dosyalarinda, calisan kod ve secret yok.\"\n\n"
            "Kod temiz ve güvenli görünüyorsa 'review_status' değerini 'PASSED' yap.\n\n"
            "⚠️ KESİN KURAL: Yanıtını SADECE ve SADECE aşağıdaki JSON formatında dön. Başka hiçbir açıklama veya metin yazma:\n"
            "{\n"
            "  \"review_status\": \"PASSED\" veya \"FAILED\",\n"
            "  \"affected_file\": \"Riskin bulunduğu dosyanın TAM ADI (diff başlığındaki '--- Dosya: ... ---' "
            "değerinden aynen kopyala). PASSED ise veya risk belirli bir dosyaya ait değilse null yaz.\",\n"
            "  \"affected_symbol\": \"Riskle ilgili değişken/fonksiyon/satır kısa alıntısı. Yoksa null yaz.\",\n"
            "  \"review_comment\": \"1-2 cümlelik Türkçe teknik tespit. FAILED ise HANGI satirin NEDEN sorun oldugunu yaz, "
            "bossa birakma. PASSED ise neyi kontrol edip temiz buldugunu yaz.\"\n"
            "}\n\n"
            f"Denetlenecek Kod Değişiklikleri:\n{code_changes}"
        )

        last_raw = ""
        for attempt in (1, 2):  # bozuk/eksik ciktiya tek retry
            try:
                llm_response = await self.llm.generate_response(
                    self.system_prompt,
                    review_prompt if attempt == 1 else (
                        review_prompt + "\n\nONCEKI YANITIN GECERSIZDI, SADECE JSON DON:\n" + last_raw[:500]
                    ),
                    response_format="json",
                    trace_name="reviewer.analyze",
                )
                last_raw = llm_response

                # Ollama bazen markdown kod blokları (```json ... ```) içine alabilir, onları temizleyelim
                clean_json = llm_response.replace("```json", "").replace("```", "").strip()
                review_result = json.loads(clean_json)

                status = str(review_result.get("review_status", "")).upper()
                if status not in ("PASSED", "FAILED"):
                    raise ValueError(f"gecersiz review_status: {status!r}")
                affected_file = review_result.get("affected_file")
                affected_symbol = review_result.get("affected_symbol")
                raw_comment = (review_result.get("review_comment") or "").strip()
                # Gerekcesiz FAILED yasak: yorumu bossa retry
                if status == "FAILED" and not raw_comment:
                    raise ValueError("FAILED gerekcesiz donduruldu")
                break
            except Exception as e:
                logger.warning(f"Reviewer deneme {attempt} basarisiz: {e}")
                status, affected_file, affected_symbol = "FAILED", None, None
                raw_comment = ""
                if attempt == 2:
                    # 2 deneme de basarisiz: fail-closed ama DURUST yorumla
                    raw_comment = (
                        "Model gecerli bir denetim uretemedi (2 deneme). "
                        "Guvenlik nedeniyle manuel incelemeye dusuruldu."
                    )
        # (for/else YOK: basarisizlik zaten except icinde islenir, break basari demek)

        if not raw_comment:
            raw_comment = "Kod analizi başarıyla tamamlandı."

        try:
            # 🎯 Yapısal alanları (affected_file/affected_symbol) serbest metinle birleştirerek
            # her zaman dosya adı içeren, izlenebilir bir yorum üretiyoruz.
            has_valid_file = affected_file and str(affected_file).lower() != "null"

            # 🛡️ EK GÜVENCE: Model FAILED derken affected_file'ı boş bırakırsa (talimata
            # rağmen), modelin işbirliğine güvenmek yerine dosya adlarını diff metninin
            # kendisinden regex ile çıkarıyoruz. Bu, modelden bağımsız, garantili bir yol.
            if status == "FAILED" and not has_valid_file:
                diff_file_names = re.findall(r"--- Dosya: (.+?) ---", code_changes)
                if diff_file_names:
                    if len(diff_file_names) == 1:
                        affected_file = diff_file_names[0]
                    else:
                        affected_file = f"{len(diff_file_names)} dosya ({', '.join(diff_file_names)})"
                    has_valid_file = True
                    logger.info(
                        f"ℹ️ Model 'affected_file' alanını doldurmadı, diff'ten otomatik "
                        f"çıkarıldı: {affected_file}"
                    )

            if has_valid_file:
                location_prefix = f"📄 {affected_file}"
                if affected_symbol and str(affected_symbol).lower() != "null":
                    location_prefix += f" ({affected_symbol})"
                composed_comment = f"{location_prefix}: {raw_comment}"
            else:
                composed_comment = raw_comment
        except Exception as e:
            # 🎯 FAIL-CLOSED son hat: yorum birlestirme bile patlarsa manuel incelemeye dusur
            logger.error(f"❌ ReviewerAgent yorum olusturamadi: {e}")
            status, composed_comment = "FAILED", (
                "Otonom denetim motoru bir yanıt üretemedi (LLM boş/bozuk çıktı döndü). "
                "Güvenlik nedeniyle bu değişiklik manuel incelemeye düşürüldü."
            )

        logger.info(f"✅ {self.name} analizi tamamladı. Sonuç: {status}")
        return {
            "agent": self.name,
            "review_status": status,
            "review_comment": composed_comment
        }

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []