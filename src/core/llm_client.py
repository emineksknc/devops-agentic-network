import logging
import ollama
from src.config.settings import settings

logger = logging.getLogger("LLMClient")

class LLMClient:
    """
    Ollama API ile asenkron iletişim kuran jenerik LLM istemcisi.
    """
    def __init__(self):
        # .env dosyasında LLM_MODEL tanımlanmadıysa varsayılan olarak llama3 kullanır
        self.model = getattr(settings, "LLM_MODEL", "llama3")

    async def generate_response(self, system_prompt: str, user_prompt: str, response_format: str = None) -> str:
        """
        Ollama kütüphanesini asenkron sarmallayarak modelden yanıt üretir.
        response_format="json" verilirse, Ollama'nın native JSON modu zorlanır.
        Bu, modelin boş/bozuk metin dönüp .replace() bant-yamalarına ihtiyaç
        duymadan JSON parse edilebilir bir çıktı üretme olasılığını artırır.
        """
        try:
            # ollama.AsyncClient kullanarak event-loop'u bloke etmeden istek atıyoruz
            client = ollama.AsyncClient()
            request_kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "options": {"temperature": 0.3}  # Teknik özetler için yaratıcılığı düşük tutuyoruz
            }
            if response_format == "json":
                request_kwargs["format"] = "json"

            response = await client.chat(**request_kwargs)
            content = response['message']['content']

            if not content or not content.strip():
                raise ValueError("Ollama boş bir yanıt döndürdü (content boş).")

            return content
        except Exception as e:
            logger.error(f"❌ Lokal LLM (Ollama) Bağlantı Hatası: {str(e)}")
            return "⚠️ Teknik bülten oluşturulurken lokal AI modeline bağlanılamadı."