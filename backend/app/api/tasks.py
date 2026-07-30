"""任务记录 API。"""



from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session



from app.db.session import get_db

from app.schemas.task import TaskRecordPageResponse

from app.services.task_log import list_task_records



router = APIRouter(prefix="/tasks", tags=["tasks"])





@router.get("", response_model=TaskRecordPageResponse)

def get_task_records(

    page: int = Query(default=1, ge=1),

    page_size: int = Query(default=10, ge=1, le=100, alias="pageSize"),

    db: Session = Depends(get_db),

) -> TaskRecordPageResponse:

    """最近任务执行记录（扫描 + 管理操作），分页返回。"""

    return list_task_records(db, page, page_size)

