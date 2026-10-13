# DAN Mimarisi (v0.2.x, `feature/web-ui`)

## Akis (LangGraph)

```
plan (LLM, sadece karar) -> github -> reviewer -> jira -> reporter
```

* LLM yalnizca **plan** kararinda kullanilir; bagimliliklar deterministik graftir (`src/agents/graph.py`).
* Guvenlik degismezleri LLM'e birakilmaz:
  * GitHub taramasi varsa **reviewer zorunludur** (plan eksikse otomatik eklenir).
  * Reviewer **fail-closed**'dur: karar uretilemezse FAILED + manuel inceleme yorumu.
  * Gerekcesiz FAILED yasaktir (retry), cift bozuk ciktida DURUST fail-closed mesaji doner.
* Reviewer iki asamalidir: serbest teknik analiz -> hukum cikartma (kisa JSON).
  Cikti katmanli parse edilir (duz JSON -> `{...}` blogu -> alan regex -> anahtar kelime).
  Bilet baglami varsa hukum ucludur: PASSED / FAILED / MISMATCH (temiz kod ama
  biletle alakasiz). MISMATCH kapilarda FAILED gibi davranir (onaya duser, bultene girmez).
* Buyuk diff'ler prompt icin kisaltilir (12k karakter); dosya listesi tam korunur.

## Baglantilar (connections)

Turler: `github | jira | llm`. Secret'lar DB'de duz metin durur, API **maskeli** doner
(`***masked***`); bos/maskeli gonderim mevcut secreti korur. **Tohumlama yoktur**:
bos DB bos envanterle acilir, herkes baglantisini UI/API ile ekler.

* GitHub: `Bearer` auth (classic + fine-grained PAT uyumu). Acik secilmis
  baglantida bos token = anonim erisim (env'ye dusmez).
* Jira: ticket varligi (`ticket_exists`) + hedef status override (`target_status`).
* LLM provider'lar (`src/core/providers.py`): `ollama | openai | anthropic | gemini`
  (gemini = Google AI Studio'ya dogrudan Generative Language API baglantisi).
  Tum alt ajanlar run'in LLM baglantisini paylasir. Model kayipsa hata,
  kurulu model listesiyle birlikte doner.

## Politika kapilari (policies)

Repo bazinda: `jira_project` (baglanti varsayilanini ezer), `on_pass/on_fail_transition`,
`auto_write_pass/fail`, `require_approval`, `dry_run_default`, baglanti eslesmeleri.
Efektif kural: `plan_on_fail = dry_run OR require_approval OR NOT auto_write_fail`,
`plan_on_pass = dry_run OR NOT auto_write_pass`. Planlanan aksiyonlar
`pending_approval`'da bekler; `POST /runs/{id}/approve` gercek yazmayi yapar.

## Run yasam dongusu

`queued -> running -> success | partially_blocked | pending_approval | failed | rejected`.
Bos run (0 commit, 0 plan) = `failed` + acik sebep. Server acilisinda yarim kalan
(`running`/`queued`) run'lar `failed`'a cekilir. Her dugum `run_events`'e yazar;
detay sayfasi timeline gosterir. `GET /api/runs/{id}` hepsini doner
(commit_units, jira_actions, events, final_report, error).

## Gozlemlenebilirlik

* LangFuse tracing (`src/core/tracing.py`): anahtar yoksa **no-op**, maliyet sifir.
  Musteriye kapali, internal ops araci olarak tasarlandi.
* Secret redaksiyonu (`redact_secrets`, varsayilan acik): Jira ozetlerine giden
  diff'lerdeki bariz kimlikler maskelenir.

## Arayuz

`frontend-react/` (Vite + React + Tailwind), `dist/` build alinip FastAPI'den
serve edilir (`dist` yoksa eski `frontend/web`'e dusulur). Sayfalar: runs,
run-detail (`/runs/:id`, bitene kadar 3 sn polling), policies, audit (salt-okunur
+ CSV/JSON export), agents (ac/kapa + prompt override), developers, settings.
Envanter endpoint'leri (`/api/github/repos`, `/api/jira/projects`) secimleri
gercek veriyle doldurur.
