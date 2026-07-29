"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, nodes, scan, settings as settings_api
from app.config import get_settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings()
    init_db()
    yield


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
