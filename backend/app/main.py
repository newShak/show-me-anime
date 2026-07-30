"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, nodes, scan, search, settings as settings_api, tags
from app.config import get_settings
from app.db.session import init_db
from app.services.watcher import start_gallery_watcher, stop_gallery_watcher


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings()
    init_db()
    start_gallery_watcher()
    yield
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
app.include_router(scan.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
