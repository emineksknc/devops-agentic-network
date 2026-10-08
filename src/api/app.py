"""DAN Web API: FastAPI + statik arayuz + SQLite."""
import logging
import sys
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api import db
from src.api.routes import agents, audit, connections, developers, policies, runs
from src.api.schemas import HealthOut

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dan.api")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "web"


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:  # Windows konsolu (cp1254) emoji print'te patlar; UTF-8'e zorla
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    db.init_db()
    logger.info("SQLite hazir: %s", db.db_path())
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

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{page}", include_in_schema=False)
    async def _page(page: str):
        candidate = FRONTEND_DIR / f"{page}.html"
        if page in {"runs", "run-detail", "policies", "audit", "agents", "developers", "settings"} and candidate.exists():
            return FileResponse(candidate)
        index = FRONTEND_DIR / "index.html"
        return FileResponse(index)
