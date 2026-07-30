"""配置读写 API。"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings, update_settings_json
from app.constants import SCAN_FAILED
from app.db.session import get_db
from app.logging_config import set_log_level
from app.schemas.settings import SettingsResponse, SettingsSaveResponse, SettingsUpdate, ThumbRebuildResponse
from app.services.task_log import TASK_REBUILD_THUMBS, record_task
from app.services.thumbnail import clear_thumbnail_cache
from app.services.watcher import start_gallery_watcher, stop_gallery_watcher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
def read_settings(settings: Settings = Depends(get_settings)) -> SettingsResponse:
    return SettingsResponse(**settings.as_public_dict())


@router.put("", response_model=SettingsSaveResponse)
def save_settings(body: SettingsUpdate) -> SettingsSaveResponse:
    old = get_settings()
    old_gallery = str(old.gallery_root)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        settings = old
        logger.debug("settings save skipped no changes")
        return SettingsSaveResponse(**settings.as_public_dict(), message="无变更", needs_rescan=False)

    logger.info("settings saving keys=%s", list(updates.keys()))
    try:
        stop_gallery_watcher()
        settings = update_settings_json(updates)
        if "log_level" in updates:
            applied = set_log_level(settings.log_level)
            logger.info("log level applied level=%s", applied)
        start_gallery_watcher()
    except ValueError as exc:
        logger.warning("settings save failed error=%s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    needs_rescan = str(settings.gallery_root) != old_gallery
    message = "配置已保存"
    if needs_rescan:
        message = "配置已保存，画廊根目录已变更，请重新扫描"
    logger.info("settings saved needs_rescan=%s gallery_root=%s", needs_rescan, settings.gallery_root)
    return SettingsSaveResponse(**settings.as_public_dict(), message=message, needs_rescan=needs_rescan)


@router.post("/rebuild-thumbs", response_model=ThumbRebuildResponse)
def rebuild_thumbs(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> ThumbRebuildResponse:
    logger.info("thumb rebuild requested")
    started = time.time()
    try:
        deleted = clear_thumbnail_cache(settings)
        message = f"已清除 {deleted} 个缩略图，访问时将按当前配置重新生成"
        record_task(db, TASK_REBUILD_THUMBS, "done", message, started_at=started, finished_at=time.time())
        return ThumbRebuildResponse(deleted=deleted, message=message)
    except OSError as exc:
        record_task(
            db,
            TASK_REBUILD_THUMBS,
            SCAN_FAILED,
            str(exc),
            started_at=started,
            finished_at=time.time(),
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
