import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas import MirrorMatchOut, MirrorRequest, MirrorResponse
from app.services import mirror_service
from app.services.dataset_service import get_default_dataset

router = APIRouter()

# In-memory per-IP sliding-window rate limit — this is the only fully
# public, unauthenticated, write-adjacent route (roadmap M8.7 explicitly
# flags it for rate limiting), so it needs a cost bound even though it's
# not persisting anything. A single-process dict is fine for this local-
# first pass; a shared store (e.g. Redis) would be needed behind >1 worker.
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 10
_request_log: dict[str, deque] = defaultdict(deque)


def _check_rate_limit(client_key: str) -> None:
    now = time.time()
    log = _request_log[client_key]
    while log and now - log[0] > RATE_LIMIT_WINDOW_SECONDS:
        log.popleft()
    if len(log) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests — please wait a moment and try again.")
    log.append(now)


@router.post("/mirror", response_model=MirrorResponse)
def mirror(
    payload: MirrorRequest,
    request: Request,
    session: Session = Depends(get_db),
) -> MirrorResponse:
    """"Mirror my story" (roadmap M8.7): unauthenticated, ad hoc — paste a
    short narrative and see the closest matches in the public seed
    dataset. No account or dataset required, and nothing about the pasted
    text is stored.
    """
    _check_rate_limit(request.client.host if request.client else "unknown")

    dataset = get_default_dataset(session)
    result = mirror_service.find_matches(session, dataset, payload.story_text, payload.top_k)

    return MirrorResponse(
        matches=[
            MirrorMatchOut(
                story_id=m.story_id,
                title=m.title,
                preview=m.preview,
                score=m.score,
                theme=m.theme,
                explanation=m.explanation,
            )
            for m in result.matches
        ],
        fingerprint=result.fingerprint,
        fingerprint_source=result.fingerprint_source,
    )
