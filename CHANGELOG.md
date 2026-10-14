# Değişiklik Günlüğü

## v0.3.0 (2026-10-14) — Web UI + otonom denetim
`feature/web-ui` dalının `master`'a ilk birleşimi. React arayüz, LangGraph akışı,
üçlü reviewer hükmü ve doğrudan Gemini desteği.

### Eklenenler
- React+Vite arayüz (7 sayfa, canlı API bağlı, `dist/` FastAPI'den sunulur).
- Reviewer üçlü hükmü: PASSED / FAILED / MISMATCH (bilet kapsam kontrolü).
- Jira bilet özeti + açıklaması okuma; kişi mührü (atanan/oluşturan) run detayında.
- Doğrudan Google Gemini provider (Generative Language API) + bağlantı testi.
- Run başı LLM mührü (provider + model), bitiş zamanı + süre rozeti.
- Run olay günlüğü (timeline), model/hüküm/metin filtreleri.
- Bilet/commit/kullanıcı derin linkleri, Jira-mavisi bilet çipleri.
- Ollama model seçici (kurulu listesi + yenile), bilinen bulut modelleri.
- `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`, `docs/ROADMAP.md`.

### Davranış kuralları (güvenlik değişmezleri)
- Reviewer zorunlu (GitHub taraması varsa), fail-closed, gerekçesiz FAILED yasak,
  koşullu MISMATCH yasak; kanıt = diff'ten birebir satır alıntısı (numara uydurmak yasak).
- Diff'ler tam boyutta gönderilir (`num_ctx=8192`); boş run = failed + açık sebep.
- Jira'ya yazma sadece onay akışıyla (dry-run / approve); tohum veri yok.

### Düzeltilenler
- Timeline event'lerinin düşmesi (emit callback kaybı), event'li detayda 500
  (`RunEventOut` importu), takılı kalan "bulunamadı" hatası.
- Bağlantı/gizli anahtar kayıpları (DB + `.env` proje köküne sabitlendi).
- Fine-grained PAT uyumu (Bearer), boş token = anonim erişim.
- Dev proxy portu (8000 → 8124) ve IPv6 `localhost` 502 sorunu.
