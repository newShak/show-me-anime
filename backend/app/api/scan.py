"""扫描 API。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import ScanJob
from app.db.session import get_db
from app.schemas.scan import ScanJobResponse
from app.services.scan_runner import is_scan_running, run_scan

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/trigger", response_model=ScanJobResponse)
def trigger_scan() -> ScanJob:
    if is_scan_running():
        raise HTTPException(status_code=409, detail="scan already running")
    job = run_scan()
    if job is None:
        raise HTTPException(status_code=409, detail="scan already running")
    return job


@router.get("/status", response_model=ScanJobResponse | None)
def scan_status(db: Session = Depends(get_db)) -> ScanJob | None:
    return db.query(ScanJob).order_by(ScanJob.id.desc()).first()
