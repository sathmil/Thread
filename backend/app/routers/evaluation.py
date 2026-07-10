import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import EvaluationQuery, EvaluationQueryExpectedStory, EvaluationResult, EvaluationRun, Story, User
from app.schemas import EvaluationResultOut, EvaluationRunOut, EvaluationRunSummaryOut
from app.services import evaluation_service
from app.services.dataset_service import get_dataset_scoped, resolve_dataset

router = APIRouter()


def _result_views(session: Session, run: EvaluationRun) -> list[EvaluationResultOut]:
    results = (
        session.execute(select(EvaluationResult).where(EvaluationResult.evaluation_run_id == run.id))
        .scalars()
        .all()
    )

    views = []
    for result in results:
        query = session.get(EvaluationQuery, result.evaluation_query_id)
        expected_ids = (
            session.execute(
                select(Story.external_id)
                .select_from(EvaluationQueryExpectedStory)
                .join(Story, Story.id == EvaluationQueryExpectedStory.story_id)
                .where(EvaluationQueryExpectedStory.evaluation_query_id == query.id)
            )
            .scalars()
            .all()
        )

        views.append(
            EvaluationResultOut(
                query=query.query_text,
                expected_story_ids=sorted(expected_ids),
                retrieved_story_ids=result.retrieved_story_ids or [],
                hit_at_k=result.hit_at_k,
                reciprocal_rank=result.reciprocal_rank,
                top_score=result.top_score,
            )
        )
    return views


def _run_out(session: Session, run: EvaluationRun) -> EvaluationRunOut:
    return EvaluationRunOut(
        run_id=str(run.id),
        embedding_model=run.embedding_model,
        unit_type=run.unit_type,
        top_k=run.top_k,
        recall_at_k=run.recall_at_k,
        mrr=run.mrr,
        precision_at_k=run.precision_at_k,
        avg_latency_ms=run.avg_latency_ms,
        created_at=run.created_at.isoformat(),
        results=_result_views(session, run),
    )


@router.get("/evaluation/run", response_model=EvaluationRunOut)
def evaluate(
    unit: str = Query("Passages"),
    top_k: int = Query(3),
    embedding_model: str = Query("Local MiniLM"),
    dataset_id: uuid.UUID | None = Query(default=None),
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> EvaluationRunOut:
    dataset = resolve_dataset(session, dataset_id, user)
    run = evaluation_service.run_evaluation(session, dataset, unit, top_k, embedding_model)
    return _run_out(session, run)


@router.get("/evaluation/runs", response_model=list[EvaluationRunSummaryOut])
def list_runs(
    dataset_id: uuid.UUID | None = Query(default=None),
    embedding_model: str | None = Query(default=None),
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[EvaluationRunSummaryOut]:
    """All persisted runs for the dataset, across every embedding model and
    over time — every call to /evaluation/run already persists a row, so
    this is what powers the historical and model-vs-model comparison views
    (roadmap M8) without any separate "save this run" step.
    """
    dataset = resolve_dataset(session, dataset_id, user)
    stmt = select(EvaluationRun).where(EvaluationRun.dataset_id == dataset.id)
    if embedding_model:
        stmt = stmt.where(EvaluationRun.embedding_model == embedding_model)
    runs = session.execute(stmt.order_by(EvaluationRun.created_at.desc())).scalars().all()

    return [
        EvaluationRunSummaryOut(
            run_id=str(run.id),
            embedding_model=run.embedding_model,
            unit_type=run.unit_type,
            top_k=run.top_k,
            recall_at_k=run.recall_at_k,
            mrr=run.mrr,
            precision_at_k=run.precision_at_k,
            avg_latency_ms=run.avg_latency_ms,
            created_at=run.created_at.isoformat(),
        )
        for run in runs
    ]


@router.get("/evaluation/runs/{run_id}", response_model=EvaluationRunOut)
def get_run(
    run_id: uuid.UUID,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> EvaluationRunOut:
    run = session.get(EvaluationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    get_dataset_scoped(session, run.dataset_id, user)
    return _run_out(session, run)
