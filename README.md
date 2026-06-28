# DevOps Agentic Network (DAN)

Lokal LLM (Ollama / Llama 3.1) destekli, dinamik karar mekanizmasına sahip otonom bir Multi-Agent DevOps entegrasyon projesi. Bu sistem; GitHub üzerindeki geliştirici aktivitelerini analiz eder, Jira panolarını otonom olarak günceller ve kurumsal sürüm raporları (Release Notes) üretir.

---

## 🎼 Proje Mimarisi (Agentic Workflow)

Proje, hardcoded (düz kod) ardışık bir pipeline yerine, gücünü **Orchestrator Agent (Şef Ajan)** mimarisinden alır. Kullanıcıdan gelen doğal dil hedefi doğrultusunda alt ajanların çalışma sırasına ve hangilerinin tetikleneceğine lokal yapay zeka kendisi karar verir.

* **GitHubAgent:** Belirtilen canlı repodan son commit geçmişini ve mesajlarını tarar. Regex pattern'leri ile `SCRUM-X` bilet ID'lerini ayıklar.
* **JiraAgent:** Ayıklanan biletleri Atlassian API üzerinden canlı panoda bulur, durumlarını otomatik olarak `In Review` aşamasına çeker ve otonom işlem raporunu yorum olarak ekler.
* **ReporterAgent:** Ham geliştirici commit mesajlarını kıdemli bir Teknik Ürün Yöneticisi (TPM) tonunda, iş odaklı kurumsal bir Türkçe Markdown Sürüm Bültenine dönüştürür.

---

## 🧠 Otonom Karar Mekanizması & Log Örneği

Sistemin esnekliğini kanıtlayan, koda dokunmadan sadece `user_goal` değiştirilerek tetiklenen otonom planlama çıktısı:
### user_goal : "GitHub reposundaki son değişiklikleri incele, ilgili Jira kartlarını güncelle ve teknik bülteni hazırla."
```json
==================================================
🧠 OLLAMA TARAFINDAN OLUŞTURULAN OTONOM İŞ PLANI:
==================================================
{
  "plan": ["github_agent", "jira_agent", "reporter_agent"],
  "reason": "GitHub'dan son commitleri okuyup Jira'daki kartları güncellemek için sırasıyla github_agent, jira_agent çalıştırılmalı, ardından reporter_agent ile teknik bülten hazırlanmalıdır."
}
==================================================
```

### user_goal : "GitHub reposundaki son değişiklikleri incele ve sadece teknik bülteni hazırla. Kesinlikle Jira kartlarında bir güncelleme yapma."
```json
==================================================
🧠 OLLAMA TARAFINDAN OLUŞTURULAN OTONOM İŞ PLANI:
==================================================
{
  "plan": ["github_agent", "reporter_agent"],
  "reason": "GitHub reposundaki son değişiklikleri incelemek için github_agent'ı çalıştırmak ve teknik bülten hazırlamak için reporter_agent'ı çalıştırmak gerekir."
}
==================================================
```

# 🛠️ Hızlı Başlangıç

### Sanal ortamı aktif edin
```./venv/Scripts/activate```

### Bağımlılıkları yükleyin
```pip install -r requirements.txt```

### Otonom sistemi tetikleyin
```python -m src.main```