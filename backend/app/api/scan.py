"""扫描 API。"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import ScanJob
from app.db.session import get_db
from app.schemas.scan import ScanJobResponse, ScanTriggerRequest
from app.services.scan_runner import is_scan_running, reconcile_stale_scan_jobs, run_scan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/trigger", response_model=ScanJobResponse)
def trigger_scan(body: ScanTriggerRequest = ScanTriggerRequest()) -> ScanJob:
    if is_scan_running():
        logger.warning("scan trigger rejected reason=already_running")
        raise HTTPException(status_code=409, detail="scan already running")
    logger.info("scan triggered via API mode=%s", body.mode)
    job = run_scan(source="api", mode=body.mode)
    if job is None:
        logger.warning("scan trigger rejected reason=lock_held")
        raise HTTPException(status_code=409, detail="scan already running")
    return job


@router.get("/status", response_model=ScanJobResponse | None)
def scan_status(db: Session = Depends(get_db)) -> ScanJob | None:
    reconcile_stale_scan_jobs(db)
    return db.query(ScanJob).order_by(ScanJob.id.desc()).first()
