"""配置读取 API。"""

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas.settings import SettingsResponse

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
def read_settings(settings: Settings = Depends(get_settings)) -> SettingsResponse:
    return SettingsResponse(**settings.as_public_dict())
