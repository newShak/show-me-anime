"""外站下载记录持久化。"""

import time

from sqlalchemy.orm import Session

from app.db.models import DownloadRecord
from app.services.download.types import DownloadJobState


def create_record(db: Session, job: DownloadJobState) -> None:
    now = time.time()
    row = DownloadRecord(
        id=job.id,
        source=job.source,
        album_id=job.album_id,
        title=job.title,
        target_rel_path=job.target_rel_path,
        status=job.status,
        progress=job.progress,
        message=job.message,
        saved_files=job.saved_files,
        created_at=now,
        finished_at=None,
    )
    db.add(row)
    db.commit()


def update_record(db: Session, job_id: str, **kwargs) -> None:
    row = db.get(DownloadRecord, job_id)
    if row is None:
        return
    for key, val in kwargs.items():
        setattr(row, key, val)
    if kwargs.get("status") in {"done", "failed"}:
        row.finished_at = time.time()
    elif kwargs.get("status") in {"pending", "running"}:
        row.finished_at = None
    db.commit()


def get_record(db: Session, job_id: str) -> DownloadRecord | None:
    return db.get(DownloadRecord, job_id)


def list_records(db: Session, page: int = 1, page_size: int = 20) -> tuple[list[DownloadRecord], int]:
    q = db.query(DownloadRecord).order_by(DownloadRecord.created_at.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def record_to_job(row: DownloadRecord) -> DownloadJobState:
    return DownloadJobState(
        id=row.id,
        source=row.source,
        album_id=row.album_id,
        title=row.title,
        target_rel_path=row.target_rel_path,
        status=row.status,
        progress=row.progress,
        message=row.message,
        saved_files=row.saved_files,
    )
