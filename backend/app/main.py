"""FastAPI 应用入口。"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import FileResponse

from app.api import download, health, library, logs, nodes, scan, search, settings as settings_api, tags, tasks
from app.config import get_settings
from app.db.session import SessionLocal, get_engine, init_db
from app.logging_config import set_log_level, setup_logging
from app.services.scan_runner import reconcile_stale_scan_jobs
from app.services.download.jobs import reconcile_stale_download_jobs
from app.services.watcher import start_gallery_watcher, stop_gallery_watcher

setup_logging(settings=get_settings())
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = PROJECT_ROOT / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    """静态资源 + Vue Router history 回退到 index.html。"""

    async def get_response(self, path: str, scope):
        is_spa_doc = False
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            response = FileResponse(STATIC_DIR / "index.html")
            is_spa_doc = True
        if is_spa_doc or path in ("", "index.html"):
            response.headers["Cache-Control"] = "no-cache"
        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    set_log_level(settings.log_level)
    logger.info(
        "starting gallery_root=%s thumb_dir=%s watch=%s log_level=%s log_dir=%s db=%s",
        settings.gallery_root,
        settings.thumb_dir,
        settings.watch_enabled,
        settings.log_level,
        settings.log_dir,
        settings.database_url,
    )
    init_db()
    db = SessionLocal(bind=get_engine())
    try:
        reconcile_stale_scan_jobs(db)
        reconcile_stale_download_jobs(db)
    finally:
        db.close()
    start_gallery_watcher()
    yield
    logger.info("shutting down")
    stop_gallery_watcher()


app = FastAPI(title="show-me-anime", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(nodes.router, prefix="/api")
app.include_router(library.router, prefix="/api")
app.include_router(scan.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(download.router, prefix="/api")

if STATIC_DIR.is_dir():
    app.mount("/", SPAStaticFiles(directory=STATIC_DIR, html=True), name="spa")
    logger.info("spa static mounted from %s", STATIC_DIR)
else:
    logger.warning("spa static dir missing: %s", STATIC_DIR)
