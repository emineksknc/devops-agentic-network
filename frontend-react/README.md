# DAN Web UI (React + Vite + Tailwind)

Backend API'sini tuketen SPA. `src/api/app.py` `dist/` varsa onu serve eder.

## Gelistirme

```powershell
cd frontend-react
npm install
npm run dev        # http://localhost:5173 (API proxy: localhost:8000)
```

## Build (backend serve eder)

```powershell
cd frontend-react
npm run build       # -> dist/
```

Sayfalar: runs, run-detail (`/runs/:id`), policies, audit, agents,
developers, settings. Tasarim token'lari `src/index.css`'te.
