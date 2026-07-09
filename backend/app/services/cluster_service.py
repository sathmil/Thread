import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Cluster, ClusterAssignment, Dataset, Story
from app.text import make_preview


def _latest_cluster_run_id(session: Session, dataset_id: uuid.UUID) -> uuid.UUID | None:
    return session.execute(
        select(Cluster.cluster_run_id)
        .where(Cluster.dataset_id == dataset_id)
        .order_by(Cluster.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_theme_by_story_external_id(session: Session, dataset_id: uuid.UUID) -> dict[str, str]:
    run_id = _latest_cluster_run_id(session, dataset_id)
    if run_id is None:
        return {}
    rows = session.execute(
        select(Story.external_id, Cluster.theme_name)
        .select_from(ClusterAssignment)
        .join(Cluster, Cluster.id == ClusterAssignment.cluster_id)
        .join(Story, Story.id == ClusterAssignment.story_id)
        .where(Cluster.cluster_run_id == run_id)
    ).all()
    return {row.external_id: row.theme_name for row in rows}


@dataclass
class ClusterStoryView:
    external_id: str
    title: str | None
    focus: str | None
    word_count: int | None
    preview: str


@dataclass
class ClusterView:
    cluster_label: int
    theme_name: str | None
    summary: str | None
    summary_source: str
    stories: list[ClusterStoryView]


def get_clusters(session: Session, dataset: Dataset) -> list[ClusterView]:
    run_id = _latest_cluster_run_id(session, dataset.id)
    if run_id is None:
        return []

    clusters = (
        session.execute(
            select(Cluster).where(Cluster.cluster_run_id == run_id).order_by(Cluster.cluster_label)
        )
        .scalars()
        .all()
    )

    views = []
    for cluster in clusters:
        story_rows = session.execute(
            select(Story)
            .select_from(ClusterAssignment)
            .join(Story, Story.id == ClusterAssignment.story_id)
            .where(ClusterAssignment.cluster_id == cluster.id)
        ).scalars().all()

        views.append(
            ClusterView(
                cluster_label=cluster.cluster_label,
                theme_name=cluster.theme_name,
                summary=cluster.summary,
                summary_source=cluster.summary_source,
                stories=[
                    ClusterStoryView(
                        external_id=story.external_id,
                        title=story.title,
                        focus=story.focus,
                        word_count=story.word_count,
                        preview=make_preview(story.story_text),
                    )
                    for story in story_rows
                ],
            )
        )
    return views
