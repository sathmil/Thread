import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import User
from app.schemas import QueryRequest, QueryResponse, ToolCallOut
from app.services import agent_service
from app.services.dataset_service import resolve_dataset

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(
    payload: QueryRequest,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> QueryResponse:
    """Conversational exploration (roadmap M8.7): the LLM agent only ever
    calls the same search/theme/fingerprint tools the rest of the app
    already exposes — see agent_service.TOOLS — so it can't retrieve or
    assert anything the UI couldn't already show directly.
    """
    dataset_id = uuid.UUID(payload.dataset_id) if payload.dataset_id else None
    dataset = resolve_dataset(session, dataset_id, user)

    result = agent_service.answer_query(session, dataset, payload.question)
    return QueryResponse(
        available=result.available,
        answer=result.answer,
        tool_calls=[ToolCallOut(tool=call["tool"], arguments=call["arguments"]) for call in result.tool_calls],
    )
