"""任务执行记录查询与写入。"""

import time

from sqlalchemy.orm import Session

from app.db.models import ScanJob, TaskLog
from app.schemas.task import TaskRecordPageResponse, TaskRecordResponse

TASK_SCAN = "scan"
TASK_REBUILD_THUMBS = "rebuild_thumbs"


def record_task(
    db: Session,
    task_type: str,
    status: str,
    message: str | None = None,
    *,
    started_at: float | None = None,
    finished_at: float | None = None,
) -> TaskLog:
    """写入一条非扫描类任务记录。"""
    row = TaskLog(
        task_type=task_type,
        status=status,
        started_at=started_at or time.time(),
        finished_at=finished_at or time.time(),
        message=message,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _scan_to_record(job: ScanJob) -> TaskRecordResponse:
    return TaskRecordResponse(
        id=job.id,
        task_type=TASK_SCAN,
        status=job.status,
        source=job.source,
        mode=job.mode,
        started_at=job.started_at,
        finished_at=job.finished_at,
        added=job.added,
        updated=job.updated,
        removed=job.removed,
        message=job.message,
    )


def _log_to_record(log: TaskLog) -> TaskRecordResponse:
    return TaskRecordResponse(
        id=log.id,
        task_type=log.task_type,
        status=log.status,
        started_at=log.started_at,
        finished_at=log.finished_at,
        message=log.message,
    )


def list_task_records(db: Session, page: int = 1, page_size: int = 10) -> TaskRecordPageResponse:
    """合并扫描任务与其他任务记录，按开始时间倒序分页。"""
    total = db.query(ScanJob).count() + db.query(TaskLog).count()
    if total == 0:
        return TaskRecordPageResponse(items=[], total=0, page=page, page_size=page_size)

    offset = (page - 1) * page_size
    fetch_n = offset + page_size
    scans = db.query(ScanJob).order_by(ScanJob.started_at.desc()).limit(fetch_n).all()
    logs = db.query(TaskLog).order_by(TaskLog.started_at.desc()).limit(fetch_n).all()

    merged = sorted(
        [_scan_to_record(job) for job in scans] + [_log_to_record(log) for log in logs],
        key=lambda item: item.started_at or 0,
        reverse=True,
    )
    items = merged[offset : offset + page_size]
    return TaskRecordPageResponse(items=items, total=total, page=page, page_size=page_size)
