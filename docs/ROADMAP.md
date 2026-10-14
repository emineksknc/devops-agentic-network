# DAN → Gerçek B2B Ürün Yol Haritası

Durum: tek kullanıcılı, tek makinelik, maskeli-secret'lı çalışan MVP (`feature/web-ui`).
Aşağıdaki fazlar sırayla, her biri tek başına dağıtıla artı değer üretir.

## Faz 0 — Ürüne kapatma (şu an buradayız, ~bitmek üzere)
- [x] Reviewer üçlü hüküm (PASSED/FAILED/MISMATCH) + kanıt kuralları
- [x] Run timeline, model mührü, süre, filtreler
- [x] `feature/web-ui` → `main` merge + sürüm etiketi (v0.3.0)
- [x] Değişiklik günlüğü (CHANGELOG) rutini

## Faz 1 — Güvenlik temeli (B2B'siz olmaz)
- Login + roller (admin / onaylayıcı / izleyici). Şu an URL'yi bilen herkes Jira'ya yazdırabilir.
- Secret'lar şifreli saklansın (SQLite düz metin duruyor) + anahtar rotasyonu.
- Onay aksiyonu kimliğe bağlansın (kimin onayladığı audit'e yazılsın).

## Faz 2 — Çok müşterili yapı
- Organizasyon/çalışma alanı izolasyonu (bağlantı + politika + run org bazında).
- Kota + maliyet takibi: run başına LLM maliyeti, org bazında limit.
- Faturalandırılabilir kullanım raporu (CSV ihraç var, modele göre genişlet).

## Faz 3 — Onay ve bildirim akışı
- Çok adımlı onay (örn. kritik repo = 2 onay), Slack/Teams'e onay kartı.
- Run iptali (koşan run'u durdurma) + zaman aşımı.
- Jira yazımı sonrası geri bildirim döngüsü (transition başarısızsa run'a yansısın).

## Faz 4 — Ölçek ve dayanıklılık
- SQLite → Postgres (çok worker), arka plan işleri kuyruğa (RQ/Celery).
- Worker + API ayrımı, Helm chart / tek komutla kurulum.
- Gerçek tracing + metrik + alarm (LangFuse no-op'tan prod gözleme).

## Faz 5 — Kurumsal uyum
- SSO (Google/Microsoft SAML/OIDC), denetim kaydında imza/zincir.
- Veri saklama politikası (run/CDN temizliği), KVKK/GDPR silme akışı.
- Reviewer doğruluk seti (golden diff'ler): model başına precision/recall, SLA eşiği.

## Bilerek kapsam dışı (şimdilik)
- GitLab/Azure DevOps/Linear entegrasyonları (talep gelirse Faz 3'e alınır).
- Arayüz İngilizce desteği (i18n) — müşteri isterse.
