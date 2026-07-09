import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import Job, User
from app.schemas import JobOut
from app.services import dataset_service

router = APIRouter()


def job_to_out(job: Job) -> JobOut:
    return JobOut(
        id=str(job.id),
        dataset_id=str(job.dataset_id),
        job_type=job.job_type,
        status=job.status,
        progress_pct=job.progress_pct,
        story_count=job.story_count,
        duration_ms=job.duration_ms,
        embedding_ms=job.embedding_ms,
        avg_embedding_ms_per_story=job.avg_embedding_ms_per_story,
        error_message=job.error_message,
        warning_message=job.warning_message,
    )


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: uuid.UUID,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> JobOut:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    dataset_service.get_dataset_scoped(session, job.dataset_id, user)
    return job_to_out(job)
