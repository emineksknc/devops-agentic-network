import re
import logging
import json
from typing import List, Dict, Any
from src.core.base_agent import BaseAgent
from src.core.llm_client import LLMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReviewerAgent")


def _parse_review_response(raw: str):
    """Katmanli parse: duz JSON -> {...} blogu -> alan regex -> anahtar kelime.
    Doner: (status | None, comment, obj)."""
    text = (raw or "").replace("```json", "").replace("```", "").strip()
    try:
        obj = json.loads(text)
        return str(obj.get("review_status", "") or "").upper(), (obj.get("review_comment") or "").strip(), obj
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            return str(obj.get("review_status", "") or "").upper(), (obj.get("review_comment") or "").strip(), obj
        except Exception:
            pass
    m = re.search(r"review_status['\"]?\s*[:=]\s*['\"]?(PASSED|FAILED|MISMATCH)", text, re.IGNORECASE)
    if m:
        return m.group(1).upper(), text[:300], {}
    up = text.upper()
    if "MISMATCH" in up and "PASSED" not in up and "FAILED" not in up:
        return "MISMATCH", text[:300], {}
    if "FAILED" in up and "PASSED" not in up:
        return "FAILED", text[:300], {}
    if "PASSED" in up and "FAILED" not in up:
        return "PASSED", text[:300], {}
    return None, "", {}


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
        # Jira bilet baglami (ozet + aciklama): graph reviewer_node doldurur.
        # Yoksa kapsam karsilastirmasi yapilmaz, MISMATCH uretilemez.
        ticket_context = (context.get("ticket_context") or "").strip()

        if not code_changes or not code_changes.strip():
            logger.warning("⚠️ ReviewerAgent'a analiz için herhangi bir kod değişikliği (diff) ulaşmadı.")
            return {
                "agent": self.name,
                "review_status": "PASSED",
                "review_comment": "Analiz edilecek kod değişikliği bulunamadı, adımlar güvenle geçildi."
            }

        logger.info(f"🧠 {self.name}: Lokal LLM (Ollama) ile otonom kod kalitesi ve güvenlik analizi başlatılıyor...")

        # Kirpma YOK: diff'in tamami prompt'a girer (izlenebilirlik + kapsama butunlugu).
        # Baglam penceresi provider'da num_ctx ile acilir; model neyi yargiladigini bilir.
        prompt_diff = code_changes
        logger.info(f"Diff tam boyutta gonderiliyor ({len(code_changes)} karakter).")

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
            + (
                "KAPSAM KURALI (bilet baglami verildi): Asagidaki Jira bilet(ler)inin istedigi is ile diff'i karsilastir. "
                "Kod temiz olsa bile biletin istedigi fonksiyonla ALAKASIZSA 'review_status' degerini 'MISMATCH' yap. "
                "MISMATCH gerekcesi SOMUT olmak zorunda: (1) bilet NE istiyor, (2) kod NE yapiyor, ikisini de yaz. "
                "KOSULLU HUKUM YASAK: 'eger / degilse / ise' ile karar verilemez ('ilgili degilse MISMATCH olur' gibi "
                "cumleler hukumsuzdur, kural hakkinda akil yurutme, KARAR ver). supheliysen PASSED ver, uydurma. "
                "Bilet baglami YOKSA MISMATCH kullanma.\n\n"
                if ticket_context else ""
            ) +
            "⚠️ KESİN KURAL: Yanıtını SADECE ve SADECE aşağıdaki JSON formatında dön. Başka hiçbir açıklama veya metin yazma:\n"
            "{\n"
            "  \"review_status\": \"PASSED\", \"FAILED\""
            + (" veya \"MISMATCH\"" if ticket_context else "") + ",\n"
            "  \"affected_file\": \"Riskin bulunduğu dosyanın TAM ADI (diff başlığındaki '--- Dosya: ... ---' "
            "değerinden aynen kopyala). PASSED ise veya risk belirli bir dosyaya ait değilse null yaz.\",\n"
            "  \"affected_symbol\": \"Riskle ilgili değişken/fonksiyon/satır kısa alıntısı. Yoksa null yaz.\",\n"
            "  \"review_comment\": \"1-2 cümlelik Türkçe teknik tespit. FAILED ise HANGI satirin NEDEN sorun oldugunu yaz, "
            "bossa birakma. PASSED ise neyi kontrol edip temiz buldugunu yaz.\"\n"
            "}\n\n"
            + (f"Beklenen Is (Jira biletleri):\n{ticket_context[:2000]}\n\n" if ticket_context else "") +
            f"Denetlenecek Kod Değişiklikleri:\n{prompt_diff}"
        )

        last_raw = ""
        status, affected_file, affected_symbol, raw_comment = "FAILED", None, None, ""
        analysis = ""
        try:
            # ADIM 1: serbest teknik analiz (modelin guclu yani, format baskisi yok)
            analyze_user = (
                "Asagidaki kod diff'ini GuVENLIK (hardcoded sifre/token/secret) ve KALITE "
                "(bariz mantik hatasi, sonsuz dongu, tehlikeli operasyon) acisindan incele. "
                "Bulursan HANGI dosyada HANGI satir oldugunu yaz. Temizse neyi kontrol ettigini yaz. "
                + (
                    "Ayrica diff'in asagidaki Jira bilet(ler)inin istedigi isi karsilayip karsilamadigini degerlendir. "
                    if ticket_context else ""
                ) +
                "En fazla 8 cumle, Turkce.\n\n"
                + (f"Beklenen Is (Jira):\n{ticket_context[:1500]}\n\n" if ticket_context else "")
                + prompt_diff
            )
            analysis = await self.llm.generate_response(
                "Sen kidemli bir DevOps guvenlik denetcisisin. Kodu teknik, kisa ve somut analiz edersin.",
                analyze_user,
                trace_name="reviewer.analyze",
            )
            if not (analysis or "").strip():
                raise ValueError("analiz bos dondu")
        except Exception as e:
            logger.warning(f"Reviewer analiz adimi basarisiz: {e}")
            analysis = ""

        for attempt in (1, 2):  # hukmu cikartma: kisa ve deterministik gorev
            try:
                if not analysis.strip():
                    raise ValueError("analiz uretilemedi")
                llm_response = await self.llm.generate_response(
                    self.system_prompt,
                    "Asagidaki KOD ANALIZINI hukme cevir. Analizde SOMUT risk (dosya+satir) varsa FAILED, "
                    + (
                        "risk yok ama kod Jira biletinin istedigi isle alakasizsa MISMATCH, "
                        "risk yok ve is karsilaniyorsa PASSED. "
                        "MISMATCH'ta biletin ne istedigini ve kodun ne yaptigini somut yaz; "
                        "kosullu (eger/degilse) hukum yasak. "
                        if ticket_context else
                        "yoksa PASSED. "
                    ) +
                    "SADECE su JSON'u don, baska hicbir sey yazma:\n"
                    '{"review_status": "PASSED, FAILED'
                    + (', MISMATCH' if ticket_context else '') +
                    '", "affected_file": "dosya adi veya null", '
                    '"affected_symbol": "ilgili satir veya null", "review_comment": "1-2 cumle Turkce gerekce"}\n\n'
                    "ANALIZ:\n" + analysis[:2000],
                    response_format="json",
                    trace_name="reviewer.verdict",
                )
                last_raw = llm_response

                status, raw_comment, review_result = _parse_review_response(llm_response)
                allowed = ("PASSED", "FAILED", "MISMATCH") if ticket_context else ("PASSED", "FAILED")
                if status not in allowed:
                    raise ValueError(f"anlasilamayan yanit: {last_raw[:120]!r}")
                affected_file = review_result.get("affected_file")
                affected_symbol = review_result.get("affected_symbol")
                # Gerekcesiz FAILED/MISMATCH yasak: yorumu bossa retry
                if status in ("FAILED", "MISMATCH") and not raw_comment:
                    raise ValueError(f"{status} gerekcesiz donduruldu")
                # Kosullu MISMATCH yasak: "eger/degilse" ile hukumsuz karar retry
                if status == "MISMATCH" and re.search(
                    r"\b(eğer|eger|değilse|degilse)\b", raw_comment, re.IGNORECASE
                ):
                    raise ValueError("MISMATCH kosullu donduruldu (karar ver, kural anlatma)")
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
