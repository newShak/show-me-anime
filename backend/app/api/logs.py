"""应用日志查看 API。"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.schemas.logs import LogContentResponse, LogFileItem, LogFileListResponse
from app.services.log_reader import list_log_files, read_log_content, resolve_log_file

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/files", response_model=LogFileListResponse)
def log_files(settings: Settings = Depends(get_settings)) -> LogFileListResponse:
    items = [LogFileItem(**row) for row in list_log_files(settings.log_dir)]
    return LogFileListResponse(
        dir=str(settings.log_dir),
        enabled=settings.log_file_enabled,
        items=items,
    )


@router.get("/content", response_model=LogContentResponse)
def log_content(
    file: str = Query(default="app.log"),
    tail_lines: int = Query(default=500, ge=1, le=5000, alias="tailLines"),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
) -> LogContentResponse:
    if not settings.log_file_enabled:
        raise HTTPException(status_code=400, detail="file logging disabled")
    try:
        path = resolve_log_file(settings.log_dir, file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload = read_log_content(path, tail_lines=tail_lines, offset=offset)
    return LogContentResponse(file=file, **payload)
