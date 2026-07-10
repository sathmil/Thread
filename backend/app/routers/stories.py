import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import Story, User
from app.schemas import FingerprintOut, JourneyEntryOut, JourneyOut, StoryDetailOut, StoryOut
from app.services import fingerprint_service, journey_service
from app.services.cluster_service import get_theme_by_story_external_id
from app.services.dataset_service import get_dataset_scoped, resolve_dataset
from app.text import make_preview

router = APIRouter()


def _get_story_scoped(session: Session, story_id: uuid.UUID, user: User | None) -> Story:
    story = session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found.")
    get_dataset_scoped(session, story.dataset_id, user)
    return story


@router.get("/stories", response_model=list[StoryOut])
def list_stories(
    dataset_id: uuid.UUID | None = Query(default=None),
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[StoryOut]:
    dataset = resolve_dataset(session, dataset_id, user)
    stories = (
        session.execute(select(Story).where(Story.dataset_id == dataset.id).order_by(Story.external_id))
        .scalars()
        .all()
    )
    return [
        StoryOut(
            id=str(story.id),
            external_id=story.external_id,
            title=story.title,
            focus=story.focus,
            word_count=story.word_count,
            preview=make_preview(story.story_text),
        )
        for story in stories
    ]


@router.get("/stories/{story_id}", response_model=StoryDetailOut)
def get_story(
    story_id: uuid.UUID,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> StoryDetailOut:
    story = _get_story_scoped(session, story_id, user)
    theme_name = get_theme_by_story_external_id(session, story.dataset_id).get(story.external_id)
    return StoryDetailOut(
        external_id=story.external_id,
        title=story.title,
        focus=story.focus,
        story_text=story.story_text,
        word_count=story.word_count,
        theme_name=theme_name,
    )


@router.get("/stories/{story_id}/fingerprint", response_model=FingerprintOut)
def get_fingerprint(
    story_id: uuid.UUID,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> FingerprintOut:
    story = _get_story_scoped(session, story_id, user)
    fingerprint = fingerprint_service.compute_fingerprint(session, story)
    return FingerprintOut(dimensions=fingerprint.dimensions, source=fingerprint.summary_source, model=fingerprint.model)


@router.get("/stories/{story_id}/journey", response_model=JourneyOut)
def get_journey(
    story_id: uuid.UUID,
    top_k: int = Query(default=3),
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> JourneyOut:
    """Nearest neighbors, a contrasting (most-dissimilar) story, and a couple
    of reflection questions drawn from this story's dominant fingerprint
    dimensions — the "Journey" concept from the roadmap's four-object model
    (Story/Theme/Journey/Insight). Journeys/contrasts are pure pgvector
    queries against embeddings already computed in M1/M6; fingerprints
    power the "why similar" explanations and reflection questions, not the
    ranking itself.
    """
    story = _get_story_scoped(session, story_id, user)
    themes = get_theme_by_story_external_id(session, story.dataset_id)
    own_theme = themes.get(story.external_id)

    nearest, farthest = journey_service.nearest_and_farthest(session, story, top_k)
    own_fingerprint = fingerprint_service.compute_fingerprint(session, story)

    def _to_entry(other: Story, score: float) -> JourneyEntryOut:
        other_fingerprint = fingerprint_service.compute_fingerprint(session, other)
        return JourneyEntryOut(
            story_id=other.external_id,
            title=other.title,
            preview=make_preview(other.story_text),
            score=round(score, 4),
            same_theme=themes.get(other.external_id) == own_theme,
            explanation=fingerprint_service.explain_similarity(own_fingerprint.dimensions, other_fingerprint.dimensions),
        )

    return JourneyOut(
        nearest=[_to_entry(other, score) for other, score in nearest],
        contrasting=_to_entry(*farthest) if farthest else None,
        reflection_questions=fingerprint_service.reflection_questions(own_fingerprint),
    )
