import uuid
from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clustering import project_embeddings
from app.config import LOCAL_MODEL_NAME
from app.models import Cluster, ClusterAssignment, Dataset, Embedding, Story, TextUnit
from app.services.embedding_columns import vector_column_for_model_id
from app.text import make_preview


def _latest_cluster_run_id(
    session: Session, dataset_id: uuid.UUID, embedding_model: str | None = None
) -> uuid.UUID | None:
    stmt = select(Cluster.cluster_run_id).where(Cluster.dataset_id == dataset_id)
    if embedding_model is not None:
        stmt = stmt.where(Cluster.embedding_model == embedding_model)
    return session.execute(stmt.order_by(Cluster.created_at.desc()).limit(1)).scalar_one_or_none()


def _run_embedding_model(session: Session, run_id: uuid.UUID) -> str | None:
    return session.execute(
        select(Cluster.embedding_model).where(Cluster.cluster_run_id == run_id).limit(1)
    ).scalar_one_or_none()


def _cluster_info_by_story_external_id(
    session: Session, dataset_id: uuid.UUID, embedding_model: str | None = None
) -> dict[str, tuple[int, str | None]]:
    run_id = _latest_cluster_run_id(session, dataset_id, embedding_model)
    if run_id is None:
        return {}
    rows = session.execute(
        select(Story.external_id, Cluster.cluster_label, Cluster.theme_name)
        .select_from(ClusterAssignment)
        .join(Cluster, Cluster.id == ClusterAssignment.cluster_id)
        .join(Story, Story.id == ClusterAssignment.story_id)
        .where(Cluster.cluster_run_id == run_id)
    ).all()
    return {row.external_id: (row.cluster_label, row.theme_name) for row in rows}


def get_theme_by_story_external_id(
    session: Session, dataset_id: uuid.UUID, embedding_model: str | None = None
) -> dict[str, str]:
    return {
        external_id: theme
        for external_id, (_, theme) in _cluster_info_by_story_external_id(
            session, dataset_id, embedding_model
        ).items()
    }


@dataclass
class ClusterStoryView:
    external_id: str
    story_uuid: str
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


def get_clusters(
    session: Session, dataset: Dataset, embedding_model: str | None = None
) -> list[ClusterView]:
    run_id = _latest_cluster_run_id(session, dataset.id, embedding_model)
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
                        story_uuid=str(story.id),
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


@dataclass
class ProjectionPoint:
    external_id: str
    story_uuid: str
    title: str | None
    preview: str
    x: float
    y: float
    cluster_label: int | None
    theme_name: str | None


def get_projection(
    session: Session, dataset: Dataset, embedding_model: str | None = None
) -> list[ProjectionPoint]:
    """2D PCA projection of whole-story embeddings, for the map view.
    Reuses app.clustering.project_embeddings() as-is (PCA is fine at this
    scale; flagged for a UMAP swap once a larger dataset lands). embedding_model
    here (like Cluster.embedding_model) is the stored model id, not a
    provider label — when not given, resolves to whichever model produced
    the most recent cluster run (falling back to the local model's id if
    none exist yet) rather than assuming MiniLM outright — correct once a
    dataset has been reindexed under a different model.
    """
    run_id = _latest_cluster_run_id(session, dataset.id, embedding_model)
    resolved_model = embedding_model or (
        _run_embedding_model(session, run_id) if run_id else LOCAL_MODEL_NAME
    )
    column = vector_column_for_model_id(resolved_model)

    rows = session.execute(
        select(Story, column)
        .select_from(Story)
        .join(TextUnit, TextUnit.story_id == Story.id)
        .join(Embedding, Embedding.text_unit_id == TextUnit.id)
        .where(
            Story.dataset_id == dataset.id,
            TextUnit.unit_type == "story",
            Embedding.embedding_model == resolved_model,
        )
        .order_by(Story.external_id)
    ).all()

    if not rows:
        return []

    stories = [row[0] for row in rows]
    vectors = np.array([row[1] for row in rows])
    coords = project_embeddings(vectors)
    cluster_info = _cluster_info_by_story_external_id(session, dataset.id, embedding_model)

    points = []
    for story, (x, y) in zip(stories, coords):
        label, theme = cluster_info.get(story.external_id, (None, None))
        points.append(
            ProjectionPoint(
                external_id=story.external_id,
                story_uuid=str(story.id),
                title=story.title,
                preview=make_preview(story.story_text, limit=160),
                x=float(x),
                y=float(y),
                cluster_label=label,
                theme_name=theme,
            )
        )
    return points
