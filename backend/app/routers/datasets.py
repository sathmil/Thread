import io
import time
import uuid

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_user
from app.data import enrich_stories
from app.deps import get_db
from app.models import Dataset, Job, Story, User
from app.routers.jobs import job_to_out
from app.schemas import DatasetCreateRequest, DatasetOut, IndexRequest, JobOut, ReindexRequest, UploadResult
from app.services import dataset_service, indexing_service
from app.tasks import index_dataset_task

router = APIRouter()


def _to_out(dataset: Dataset) -> DatasetOut:
    return DatasetOut(
        id=str(dataset.id),
        name=dataset.name,
        description=dataset.description,
        visibility=dataset.visibility,
        status=dataset.status,
        owner_user_id=str(dataset.owner_user_id) if dataset.owner_user_id else None,
    )


def _require_owner(dataset: Dataset, user: User) -> None:
    if dataset.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the dataset owner can do that.")


def _run_index_job(session: Session, dataset: Dataset, embedding_model: str, job_type: str) -> Job:
    """Shared by /index and /reindex — same sync-vs-async threshold, same
    Celery task, only the recorded job_type differs. Idempotent chunking in
    indexing_service.index_dataset() is what makes calling this safe for
    both "first index" and "reindex under a different model."
    """
    story_count = session.query(Story).filter(Story.dataset_id == dataset.id).count()

    job = Job(dataset_id=dataset.id, job_type=job_type, status="queued", story_count=story_count)
    session.add(job)
    session.commit()
    session.refresh(job)

    if story_count < indexing_service.SYNC_INDEX_THRESHOLD:
        # Small dataset: embed inline for a snappier UX (roadmap M6 decision).
        start = time.perf_counter()
        job.status = "running"
        dataset.status = "indexing"
        session.commit()
        try:
            def _on_progress(pct: int) -> None:
                job.progress_pct = pct
                session.commit()

            result = indexing_service.index_dataset(
                session, dataset, embedding_model, on_progress=_on_progress
            )
            indexing_service.cluster_dataset(session, dataset, result.actual_embedding_model)
            job.status = "succeeded"
            job.progress_pct = 100
            job.story_count = result.story_count
            job.embedding_ms = result.embedding_ms
            job.avg_embedding_ms_per_story = (
                result.embedding_ms / result.story_count if result.story_count else None
            )
            job.warning_message = result.warning
            job.duration_ms = (time.perf_counter() - start) * 1000
            dataset.status = "ready"
            session.commit()
        except Exception as exc:
            session.rollback()
            job.status = "failed"
            job.error_message = str(exc)
            session.commit()
    else:
        task = index_dataset_task.delay(str(job.id), str(dataset.id), embedding_model)
        job.celery_task_id = task.id
        session.commit()

    session.refresh(job)
    return job


@router.get("/datasets", response_model=list[DatasetOut])
def list_datasets(
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[DatasetOut]:
    datasets = dataset_service.list_datasets_for_user(session, user)
    return [_to_out(d) for d in datasets]


@router.post("/datasets", response_model=DatasetOut, status_code=201)
def create_dataset(
    payload: DatasetCreateRequest,
    user: User = Depends(require_user),
    session: Session = Depends(get_db),
) -> DatasetOut:
    dataset = dataset_service.create_dataset(session, user, payload.name, payload.description)
    return _to_out(dataset)


@router.get("/datasets/{dataset_id}", response_model=DatasetOut)
def get_dataset(
    dataset_id: uuid.UUID,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> DatasetOut:
    dataset = dataset_service.get_dataset_scoped(session, dataset_id, user)
    return _to_out(dataset)


@router.post("/datasets/{dataset_id}/upload", response_model=UploadResult)
async def upload_stories(
    dataset_id: uuid.UUID,
    file: UploadFile,
    user: User = Depends(require_user),
    session: Session = Depends(get_db),
) -> UploadResult:
    dataset = dataset_service.get_dataset_scoped(session, dataset_id, user)
    _require_owner(dataset, user)

    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {exc}") from exc

    if "story_text" not in df.columns:
        raise HTTPException(status_code=422, detail="CSV must have a 'story_text' column.")

    existing_count = session.query(Story).filter(Story.dataset_id == dataset.id).count()
    if "id" not in df.columns:
        df["id"] = [str(existing_count + i + 1) for i in range(len(df))]
    df["id"] = df["id"].astype(str).str.zfill(3)
    df["story_text"] = df["story_text"].fillna("")

    enriched = enrich_stories(df)
    enriched["source"] = dataset.name

    created = 0
    for _, row in enriched.iterrows():
        session.add(
            Story(
                dataset_id=dataset.id,
                external_id=row["id"],
                title=row["title"],
                focus=row["focus"],
                story_text=row["story_text"],
                word_count=int(row["word_count"]),
                source=row["source"],
            )
        )
        created += 1
    session.commit()

    return UploadResult(stories_created=created)


@router.post("/datasets/{dataset_id}/index", response_model=JobOut, status_code=202)
def index_dataset(
    dataset_id: uuid.UUID,
    payload: IndexRequest,
    user: User = Depends(require_user),
    session: Session = Depends(get_db),
) -> JobOut:
    dataset = dataset_service.get_dataset_scoped(session, dataset_id, user)
    _require_owner(dataset, user)
    job = _run_index_job(session, dataset, payload.embedding_model, job_type="index")
    return job_to_out(job)


@router.post("/datasets/{dataset_id}/reindex", response_model=JobOut, status_code=202)
def reindex_dataset(
    dataset_id: uuid.UUID,
    payload: ReindexRequest,
    user: User = Depends(require_user),
    session: Session = Depends(get_db),
) -> JobOut:
    """Recomputes embeddings under a different model without deleting the
    existing ones — indexing_service.index_dataset() only adds Embedding
    rows for (text_unit, model, version) combinations that don't already
    exist, so the old model's embeddings and clusters stay queryable
    alongside the new ones for comparison.
    """
    dataset = dataset_service.get_dataset_scoped(session, dataset_id, user)
    _require_owner(dataset, user)
    job = _run_index_job(session, dataset, payload.embedding_model, job_type="reindex")
    return job_to_out(job)
