# DAN Operasyon Rehberi

## Portlar (bu makine)

| Port | Sahibi        |
| ---- | ------------- |
| 8000 | `Manager.exe` (baska uygulama, dokunma) |
| 8123 | ClickHouse (LangFuse yigini, dokunma)    |
| 8124 | **DAN**                                    |

Baslatma: `.\start-dan.ps1` (proje kokunden).

## Altin kural: pull + build + restart

Push dosyalari diske indirir; **calisan server eski kodu serve eder.**
Her `git pull` sonrasi sirasıyla:

```powershell
git pull
cd frontend-react; npm run build; cd ..
# server'i durdurup baslat (start-dan.ps1)
```

`dist/` repoya girmez; build alinmazsa backend bir onceki build'i serve eder.

## Yollar sabittir

* `DAN_DB_PATH` ve `.env` proje kokune sabitlidir; server nereden
  baslatilirsa baslatilsin ayni DB ve ayar okunur.
* `.env` yoksa kod default'lari gecerlidir (`llama3` gibi) — bu yuzden
  kritik ayarlar (ozellikle `LLM_MODEL`) DB'deki **LLM baglantisinda**
  durmalidir, `.env`'ye guvenilmemelidir.

## Token yonetimi (UI)

* Tokenlar yalnizca Ayarlar sayfasindan girilir (DB'de sifreli, API'de maskeli).
  Tek istisna: admin "Göster"e basarsa tek seferlik acar (kullanim loga duser).
* **Anahtar yedegi:** `data/secret.key` (veya `DAN_SECRET_KEY`) kaybolursa kayitli
  token'lar COZULEMEZ. Dosyayi yedekle, repoya koyma, kimseyle paylasma.
* Test butonu once kaydeder, sonra dener; sonuc kalici satirda yazar.
* GitHub fine-grained PAT: ilgili repo **Repository access**'te secili olmali,
  yoksa `403 Resource not accessible` verir (repo YOK degil, YETKI yok).
* Jira: dogru site adresi (`...atlassian.net`), e-posta + API token.
* Tavsiye: `test.env`, `.env1` gibi dosyalar repoya GIRMESIN (`.gitignore`).

## Arizalar ve anlamlari

| Belirti | Anlam | Cozum |
| ------- | ----- | ----- |
| Run `failed` + `GitHub API 401` | Token olu/yetkisiz | Token yenile, Kaydet + Test |
| Run `failed` + `403 Resource not accessible` | Token repoyu goremiyor | Repository access'e repo ekle |
| `model 'X' kurulu degil` | Ollama'da model yok | Kurulu model sec (Ayarlar > LLM) veya `ollama pull` |
| Hep FAILED + "2 deneme" | Model kararsiz/zayif | Daha guclu model dene; diff'ler cok buyukse normal |
| Sayfa guncellenmiyor | Eski server / eski build | pull + build + restart |
| `pending_approval` | Plan onay bekliyor | Detaydan Onayla/Reddet |
| Port cakismasi | Baska surec tutuyor | `Get-NetTCPConnection -LocalPort 8124` ile bul, oldur |

## Test

```powershell
.\venv\Scripts\python.exe -m pytest tests/ -q
```

CI (`.github/workflows/ci-cd.yml`) her push'ta compile + test kosar.
