"""任务记录 API。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.task import TaskPurgeRequest, TaskPurgeResponse, TaskRecordPageResponse
from app.services.task_log import list_task_records, purge_task_records

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskRecordPageResponse)
def get_task_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
) -> TaskRecordPageResponse:
    """最近任务执行记录（扫描 + 管理操作），分页返回。"""
    return list_task_records(db, page, page_size)


@router.post("/purge", response_model=TaskPurgeResponse)
def purge_task_records_api(
    body: TaskPurgeRequest,
    db: Session = Depends(get_db),
) -> TaskPurgeResponse:
    """按开始时间范围删除任务记录。"""
    if body.start_time > body.end_time:
        raise HTTPException(status_code=400, detail="startTime must be <= endTime")
    return purge_task_records(db, body.start_time, body.end_time)
