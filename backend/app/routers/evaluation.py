from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import EvaluationQuery, EvaluationQueryExpectedStory, EvaluationResult, Story
from app.schemas import EvaluationResultOut, EvaluationRunOut
from app.services import evaluation_service
from app.services.dataset_service import get_default_dataset

router = APIRouter()


@router.get("/evaluation/run", response_model=EvaluationRunOut)
def evaluate(
    unit: str = Query("Passages"),
    top_k: int = Query(3),
    embedding_model: str = Query("Local MiniLM"),
    session: Session = Depends(get_db),
) -> EvaluationRunOut:
    dataset = get_default_dataset(session)
    run = evaluation_service.run_evaluation(session, dataset, unit, top_k, embedding_model)

    results = (
        session.execute(select(EvaluationResult).where(EvaluationResult.evaluation_run_id == run.id))
        .scalars()
        .all()
    )

    result_views = []
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

        result_views.append(
            EvaluationResultOut(
                query=query.query_text,
                expected_story_ids=sorted(expected_ids),
                retrieved_story_ids=result.retrieved_story_ids or [],
                hit_at_k=result.hit_at_k,
                reciprocal_rank=result.reciprocal_rank,
                top_score=result.top_score,
            )
        )

    return EvaluationRunOut(
        run_id=str(run.id),
        embedding_model=run.embedding_model,
        unit_type=run.unit_type,
        top_k=run.top_k,
        recall_at_k=run.recall_at_k,
        mrr=run.mrr,
        avg_latency_ms=run.avg_latency_ms,
        results=result_views,
    )
