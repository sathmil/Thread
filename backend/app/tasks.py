import time
import uuid

from app.celery_app import celery_app
from app.db import SessionLocal
from app.models import Dataset, Job
from app.services import indexing_service


@celery_app.task(bind=True)
def index_dataset_task(self, job_id: str, dataset_id: str, embedding_model: str = "Local MiniLM") -> None:
    session = SessionLocal()
    start = time.perf_counter()
    try:
        job = session.get(Job, uuid.UUID(job_id))
        dataset = session.get(Dataset, uuid.UUID(dataset_id))
        if job is None or dataset is None:
            return

        job.status = "running"
        job.celery_task_id = self.request.id
        dataset.status = "indexing"
        session.commit()

        def _on_progress(pct: int) -> None:
            job.progress_pct = pct
            session.commit()

        result = indexing_service.index_dataset(session, dataset, embedding_model, on_progress=_on_progress)
        job.story_count = result.story_count
        job.embedding_ms = result.embedding_ms
        job.avg_embedding_ms_per_story = (
            result.embedding_ms / result.story_count if result.story_count else None
        )
        job.progress_pct = 90
        session.commit()

        if result.story_count > indexing_service.ASYNC_CLUSTER_THRESHOLD:
            job.status = "succeeded"
            job.progress_pct = 95
            job.duration_ms = (time.perf_counter() - start) * 1000
            dataset.status = "ready"
            session.commit()
            cluster_dataset_task.delay(dataset_id, embedding_model)
        else:
            indexing_service.cluster_dataset(session, dataset, embedding_model)
            job.status = "succeeded"
            job.progress_pct = 100
            job.duration_ms = (time.perf_counter() - start) * 1000
            dataset.status = "ready"
            session.commit()
    except Exception as exc:
        session.rollback()
        job = session.get(Job, uuid.UUID(job_id))
        if job is not None:
            job.status = "failed"
            job.error_message = str(exc)
            session.commit()
        raise
    finally:
        session.close()


@celery_app.task
def cluster_dataset_task(dataset_id: str, embedding_model: str = "Local MiniLM") -> None:
    session = SessionLocal()
    try:
        dataset = session.get(Dataset, uuid.UUID(dataset_id))
        if dataset is None:
            return
        indexing_service.cluster_dataset(session, dataset, embedding_model)
    finally:
        session.close()
