"""健康检查 API。"""

from fastapi import APIRouter

from app.version import read_app_version

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "version": read_app_version()}
