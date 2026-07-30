"""配置读写 API。"""

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings, update_settings_json
from app.schemas.settings import SettingsResponse, SettingsSaveResponse, SettingsUpdate
from app.services.watcher import start_gallery_watcher, stop_gallery_watcher

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
        return SettingsSaveResponse(**settings.as_public_dict(), message="无变更", needs_rescan=False)

    try:
        stop_gallery_watcher()
        settings = update_settings_json(updates)
        start_gallery_watcher()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    needs_rescan = str(settings.gallery_root) != old_gallery
    message = "配置已保存"
    if needs_rescan:
        message = "配置已保存，画廊根目录已变更，请重新扫描"
    return SettingsSaveResponse(**settings.as_public_dict(), message=message, needs_rescan=needs_rescan)
