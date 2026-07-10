import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import InsightFinding, Story, User
from app.schemas import InsightFindingOut
from app.services import insight_service
from app.services.dataset_service import get_dataset_scoped

router = APIRouter()


@router.get("/datasets/{dataset_id}/insights", response_model=list[InsightFindingOut])
def get_insights(
    dataset_id: uuid.UUID,
    embedding_model: str | None = Query(default=None),
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[InsightFindingOut]:
    """Returns the dataset's persisted insight findings, computing and
    caching them on first request (like fingerprints/journeys) rather than
    recomputing on every page load — see insight_service.generate_findings.
    """
    dataset = get_dataset_scoped(session, dataset_id, user)

    findings = (
        session.execute(select(InsightFinding).where(InsightFinding.dataset_id == dataset.id))
        .scalars()
        .all()
    )
    if not findings:
        findings = insight_service.generate_findings(session, dataset, embedding_model)

    story_ids = {f.subject_story_id for f in findings if f.subject_story_id is not None}
    stories_by_id = (
        {s.id: s for s in session.execute(select(Story).where(Story.id.in_(story_ids))).scalars().all()}
        if story_ids
        else {}
    )

    def _story_field(finding: InsightFinding, field: str) -> str | None:
        story = stories_by_id.get(finding.subject_story_id)
        return getattr(story, field) if story is not None else None

    return [
        InsightFindingOut(
            finding_type=f.finding_type,
            finding_text=f.finding_text,
            dimension_a=f.dimension_a,
            dimension_b=f.dimension_b,
            effect_size=f.effect_size,
            sample_size=f.sample_size,
            subject_story_external_id=_story_field(f, "external_id"),
            subject_story_uuid=str(f.subject_story_id) if f.subject_story_id else None,
            subject_story_title=_story_field(f, "title"),
        )
        for f in findings
    ]
