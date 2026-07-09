from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas import ClusterOut, ClusterStoryOut
from app.services import cluster_service
from app.services.dataset_service import get_default_dataset

router = APIRouter()


@router.get("/clusters", response_model=list[ClusterOut])
def list_clusters(session: Session = Depends(get_db)) -> list[ClusterOut]:
    dataset = get_default_dataset(session)
    clusters = cluster_service.get_clusters(session, dataset)
    return [
        ClusterOut(
            cluster_label=c.cluster_label,
            theme_name=c.theme_name,
            summary=c.summary,
            summary_source=c.summary_source,
            stories=[
                ClusterStoryOut(
                    external_id=s.external_id,
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
