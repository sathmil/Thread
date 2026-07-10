import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import User
from app.schemas import ClusterOut, ClusterStoryOut, ProjectionPointOut
from app.services import cluster_service
from app.services.dataset_service import resolve_dataset

router = APIRouter()


@router.get("/clusters", response_model=list[ClusterOut])
def list_clusters(
    dataset_id: uuid.UUID | None = Query(default=None),
    embedding_model: str | None = Query(default=None),
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[ClusterOut]:
    dataset = resolve_dataset(session, dataset_id, user)
    clusters = cluster_service.get_clusters(session, dataset, embedding_model)
    return [
        ClusterOut(
            cluster_label=c.cluster_label,
            theme_name=c.theme_name,
            summary=c.summary,
            summary_source=c.summary_source,
            stories=[
                ClusterStoryOut(
                    external_id=s.external_id,
                    story_uuid=s.story_uuid,
                    title=s.title,
                    focus=s.focus,
                    word_count=s.word_count,
                    preview=s.preview,
                )
                for s in c.stories
            ],
        )
        for c in clusters
    ]


@router.get("/clusters/projection", response_model=list[ProjectionPointOut])
def get_projection(
    dataset_id: uuid.UUID | None = Query(default=None),
    embedding_model: str | None = Query(default=None),
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[ProjectionPointOut]:
    dataset = resolve_dataset(session, dataset_id, user)
    points = cluster_service.get_projection(session, dataset, embedding_model)
    return [
        ProjectionPointOut(
            external_id=p.external_id,
            story_uuid=p.story_uuid,
            title=p.title,
            preview=p.preview,
            x=p.x,
            y=p.y,
            cluster_label=p.cluster_label,
            theme_name=p.theme_name,
        )
        for p in points
    ]
