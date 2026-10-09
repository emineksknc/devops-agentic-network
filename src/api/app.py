"""DAN Web API: FastAPI + statik arayuz + SQLite."""
import logging
import sys
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api import db
from src.api.routes import agents, audit, connections, developers, inventory, llm, policies, runs, settings as app_settings, webhooks
from src.api.schemas import HealthOut

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dan.api")

ROOT_DIR = Path(__file__).resolve().parents[2]
DIST_DIR = ROOT_DIR / "frontend-react" / "dist"
LEGACY_DIR = ROOT_DIR / "frontend" / "web"
# React build varsa onu serve et, yoksa eski statik arayuze dus
USE_DIST = (DIST_DIR / "index.html").exists()
FRONTEND_DIR = DIST_DIR if USE_DIST else LEGACY_DIR

SPA_PAGES = {"runs", "run-detail", "policies", "audit", "agents", "developers", "settings"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:  # Windows konsolu (cp1254) emoji print'te patlar; UTF-8'e zorla
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    db.init_db()
    logger.info("SQLite hazir: %s", db.db_path())
    # Yarim kalan run'lar: server restart'inda arka plan gorevi olur, status sonsuza
    # dek 'running'/'queued' kalir. Acilista bunlari dusur.
    try:
        with db.connect() as conn:
            cur = conn.execute(
                "UPDATE runs SET status='failed', error='server yeniden baslatildi, run yarim kaldi'"
                " WHERE status IN ('running','queued')"
            )
            if cur.rowcount:
                logger.warning("%d yarim run 'failed'a cekildi.", cur.rowcount)
    except Exception as e:
        logger.warning("stale run temizligi atlandi: %s", e)
    yield


app = FastAPI(title="DevOps Agentic Network", version="0.2.0", lifespan=lifespan)


@app.get("/api/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(data={"frontend": FRONTEND_DIR.exists()})


app.include_router(runs.router)
app.include_router(policies.router)
app.include_router(connections.router)
app.include_router(agents.router)
app.include_router(developers.router)
app.include_router(audit.router)
app.include_router(llm.router)
app.include_router(app_settings.router)
app.include_router(webhooks.router)
app.include_router(inventory.router)

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def _index():
        return FileResponse(FRONTEND_DIR / "index.html")

    if USE_DIST:
        # React SPA: sayfa route'lari index'e duser, ic routing client'ta
        @app.get("/{full_path:path}", include_in_schema=False)
        async def _spa(full_path: str):
            if full_path.startswith("assets/"):
                candidate = DIST_DIR / full_path
                if candidate.is_file():
                    return FileResponse(candidate)
            name = full_path.split("/")[0]
            name = name[:-5] if name.endswith(".html") else name
            if name in SPA_PAGES:
                return FileResponse(DIST_DIR / "index.html")
            return FileResponse(DIST_DIR / "index.html")
    else:

        @app.get("/{page}", include_in_schema=False)
        async def _page(page: str):
            name = page[:-5] if page.endswith(".html") else page
            candidate = FRONTEND_DIR / f"{name}.html"
            if name in SPA_PAGES and candidate.exists():
                return FileResponse(candidate)
            index = FRONTEND_DIR / "index.html"
            return FileResponse(index)

    # Sablon ici *.html linkler + dogrudan dosya erisimi icin statik fallback (en sonda)
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
