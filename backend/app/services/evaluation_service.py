import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Dataset, EvaluationQuery, EvaluationQueryExpectedStory, EvaluationResult, EvaluationRun, Story
from app.services import search_service

# Large enough to cover every text unit in a small dataset, so reciprocal-rank
# calculation sees the true rank rather than being truncated at top_k. At real
# scale this should be capacity-bounded instead of "fetch everything".
_FULL_RANKING_LIMIT = 10_000


def run_evaluation(
    session: Session,
    dataset: Dataset,
    unit: str = "Passages",
    top_k: int = 3,
    provider: str = "Local MiniLM",
) -> EvaluationRun:
    queries = (
        session.execute(select(EvaluationQuery).where(EvaluationQuery.dataset_id == dataset.id))
        .scalars()
        .all()
    )

    recall_hits: list[int] = []
    reciprocal_ranks: list[float] = []
    latencies: list[float] = []
    pending_results: list[dict] = []

    for query in queries:
        expected_ids = set(
            session.execute(
                select(Story.external_id)
                .select_from(EvaluationQueryExpectedStory)
                .join(Story, Story.id == EvaluationQueryExpectedStory.story_id)
                .where(EvaluationQueryExpectedStory.evaluation_query_id == query.id)
            )
            .scalars()
            .all()
        )

        start = time.perf_counter()
        results, _ = search_service.search(session, dataset, query.query_text, unit, _FULL_RANKING_LIMIT, provider)
        latency_ms = (time.perf_counter() - start) * 1000
        latencies.append(latency_ms)

        ranked_ids = [r.story_id for r in results]
        first_rank = next((idx + 1 for idx, sid in enumerate(ranked_ids) if sid in expected_ids), None)
        top_ids = ranked_ids[:top_k]
        hit = any(sid in expected_ids for sid in top_ids)

        reciprocal_rank = (1 / first_rank) if first_rank else 0.0
        reciprocal_ranks.append(reciprocal_rank)
        recall_hits.append(1 if hit else 0)

        pending_results.append(
            dict(
                evaluation_query_id=query.id,
                retrieved_story_ids=top_ids,
                hit_at_k=hit,
                reciprocal_rank=reciprocal_rank,
                top_score=results[0].score if results else None,
                latency_ms=latency_ms,
            )
        )

    run = EvaluationRun(
        dataset_id=dataset.id,
        embedding_model=provider,
        unit_type=unit,
        top_k=top_k,
        recall_at_k=(sum(recall_hits) / len(recall_hits)) if recall_hits else 0.0,
        mrr=(sum(reciprocal_ranks) / len(reciprocal_ranks)) if reciprocal_ranks else 0.0,
        avg_latency_ms=(sum(latencies) / len(latencies)) if latencies else None,
    )
    session.add(run)
    session.flush()

    for payload in pending_results:
        session.add(EvaluationResult(evaluation_run_id=run.id, **payload))

    session.commit()
    return run
