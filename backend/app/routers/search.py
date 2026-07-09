import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import SearchLog, User
from app.schemas import SearchRequest, SearchResponse, SearchResultOut
from app.services import search_service
from app.services.dataset_service import resolve_dataset

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SearchResponse:
    dataset_id = uuid.UUID(payload.dataset_id) if payload.dataset_id else None
    dataset = resolve_dataset(session, dataset_id, user)

    start = time.perf_counter()
    try:
        results, embedding_ms = search_service.search(
            session, dataset, payload.query, payload.unit, payload.top_k, payload.embedding_model
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    latency_ms = (time.perf_counter() - start) * 1000

    session.add(
        SearchLog(
            dataset_id=dataset.id,
            user_id=user.id if user else None,
            query_text=payload.query,
            unit_type=payload.unit,
            embedding_model=payload.embedding_model,
            top_k=payload.top_k,
            latency_ms=latency_ms,
            embedding_ms=embedding_ms,
        )
    )
    session.commit()

    return SearchResponse(
        query=payload.query,
        unit=payload.unit,
        results=[
            SearchResultOut(
                story_id=r.story_id,
                unit_type=r.unit_type,
                unit_index=r.unit_index,
                text_unit=r.text_unit,
                preview=r.preview,
                score=round(r.score, 4),
                theme=r.theme,
            )
            for r in results
        ],
    )
