# Frontend (Web UI)

Stitch mobil sablonlarindan uretilen web uyarlamasi.

## Yapi

- `web/` — tarayicida acilabilen sayfalar (build ciktisi, repoda tutulur)
  - `runs.html`, `run-detail.html`, `policies.html`, `audit.html`, `settings.html`
  - `assets/web.css` — desktop duzen katmani (sidebar, grid)
  - `assets/web.js` — aktif sayfa isaretleme
- `tools/build_web.py` — mobil `code.html` kaynaklarindan web ciktisi uretir

## Web uyarlamasi (mobil -> web)

- Alt navigasyon bar mobilde kalir (`lg:hidden`), desktop'ta gizlenir
- Cekmece menu desktop'ta sabit sidebar olur (`#mobile-nav-drawer`, 240px)
- Header + icerik sidebar genisligi kadar sagdan baslar, icerik max 1400px
- Run listesi genis ekranda 2 sutun grid olur
- Sayfalar arasi linkler baglandi: calistirmalar <-> detay <-> politikalar <-> denetim <-> ayarlar
- Detay sayfasinda sidebar + "Tum Calistirmalar" kirintisi eklendi

## Yeniden uretme

Sablon guncellenirse (Stitch'ten yeni `code.html`):

```powershell
.\venv\Scripts\python.exe frontend/tools/build_web.py
```

Not: `stitch_devops_agentic_network_dashboard/` klasoru `.gitignore`'da
oldugu icin repoya girmez; sablon degisikliginde klasoru lokalde tutup
ustteki komutu calistirmak yeterlidir.
