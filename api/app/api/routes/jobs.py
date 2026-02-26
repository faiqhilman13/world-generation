import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as OrmSession

from app.api.deps import db_session
from app.core.config import get_settings
from app.db.models import WorldJob
from app.schemas.jobs import JobResponse
from app.services.session_service import get_or_create_session

router = APIRouter()


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    request: Request,
    db: OrmSession = Depends(db_session),
) -> JobResponse:
    settings = get_settings()
    sid = request.cookies.get(settings.session_cookie_name)
    session = get_or_create_session(db, sid)

    try:
        parsed_job_id = uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc

    job = (
        db.query(WorldJob)
        .filter(WorldJob.id == parsed_job_id, WorldJob.session_id == session.id)
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    error = None
    if job.error_code or job.error_message:
        error = {
            "code": job.error_code,
            "message": job.error_message,
        }

    return JobResponse(
        job_id=str(job.id),
        status=job.status,
        progress_percent=job.progress_percent,
        provider_operation_id=job.provider_operation_id,
        world_id=job.provider_world_id,
        error=error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
