import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clustering import cluster_stories, summarize_cluster
from app.embeddings import embed_texts
from app.models import Cluster, ClusterAssignment, Dataset, Embedding, Story, TextUnit
from app.text import make_preview, split_text_units

UNIT_LABEL_TO_TYPE = {"Sentences": "sentence", "Passages": "passage", "Stories": "story"}

# Safeguard against pathological unit counts on very long stories — caps
# how many sentence/passage units a single story can contribute.
MAX_UNITS_PER_STORY = {"sentence": 200, "passage": 60, "story": 1}

# Below this many stories, POST /datasets/{id}/index runs synchronously in
# the request for a snappier UX; at or above it, indexing always goes
# through Celery (roadmap M6 design decision).
SYNC_INDEX_THRESHOLD = 25

# Above this many stories, clustering is dispatched as its own chained
# Celery task rather than run inline at the end of indexing.
ASYNC_CLUSTER_THRESHOLD = 25

# Stories per embedding batch — keeps progress reporting granular (and
# commits incrementally) regardless of dataset size, instead of one giant
# embed_texts() call per unit type with no visible movement in between.
STORY_BATCH_SIZE = 20


@dataclass
class IndexResult:
    story_count: int
    embedding_ms: float


def index_dataset(
    session: Session,
    dataset: Dataset,
    embedding_model: str = "Local MiniLM",
    on_progress: Callable[[int], None] | None = None,
) -> IndexResult:
    """Chunks + embeds every story in the dataset, in batches, reporting
    progress (0-90, the last 10 is reserved for clustering) via on_progress
    after each batch. Reuses app.text/app.embeddings as-is — this is a
    persistence-layer operation, not a retrieval-logic rewrite. Does not
    cluster; call cluster_dataset() separately (sync or async).
    """
    stories = (
        session.execute(select(Story).where(Story.dataset_id == dataset.id).order_by(Story.external_id))
        .scalars()
        .all()
    )

    embedding_ms_total = 0.0
    batches_per_unit = max(1, (len(stories) + STORY_BATCH_SIZE - 1) // STORY_BATCH_SIZE)
    total_batches = len(UNIT_LABEL_TO_TYPE) * batches_per_unit
    completed_batches = 0

    for unit_label, unit_type in UNIT_LABEL_TO_TYPE.items():
        cap = MAX_UNITS_PER_STORY[unit_type]

        for batch_start in range(0, max(len(stories), 1), STORY_BATCH_SIZE):
            batch = stories[batch_start : batch_start + STORY_BATCH_SIZE]
            unit_texts: list[str] = []
            unit_refs: list[tuple[Story, int]] = []

            for story in batch:
                parts = split_text_units(story.story_text, unit_label)[:cap]
                for unit_index, part in enumerate(parts, start=1):
                    unit_texts.append(part)
                    unit_refs.append((story, unit_index))

            if unit_texts:
                start = time.perf_counter()
                vectors = embed_texts(unit_texts, embedding_model)
                embedding_ms_total += (time.perf_counter() - start) * 1000

                for (story, unit_index), text, vector in zip(unit_refs, unit_texts, vectors):
                    text_unit = TextUnit(
                        story_id=story.id,
                        unit_type=unit_type,
                        unit_index=unit_index,
                        text_unit=text,
                        preview=make_preview(text, limit=260),
                    )
                    session.add(text_unit)
                    session.flush()

                    session.add(
                        Embedding(
                            text_unit_id=text_unit.id,
                            embedding_model=embedding_model,
                            embedding_version="v1",
                            vector_384=vector.tolist(),
                            dim=len(vector),
                        )
                    )
                session.commit()

            completed_batches += 1
            if on_progress:
                on_progress(min(90, int(completed_batches / total_batches * 90)))

    return IndexResult(story_count=len(stories), embedding_ms=embedding_ms_total)


def cluster_dataset(session: Session, dataset: Dataset, embedding_model: str = "Local MiniLM") -> None:
    """KMeans over whole-story embeddings, re-queried from the DB (rather than
    passed in-memory) so this can run standalone as its own Celery task,
    independent from whichever process ran index_dataset().
    """
    rows = session.execute(
        select(Story, Embedding.vector_384)
        .select_from(Story)
        .join(TextUnit, TextUnit.story_id == Story.id)
        .join(Embedding, Embedding.text_unit_id == TextUnit.id)
        .where(
            Story.dataset_id == dataset.id,
            TextUnit.unit_type == "story",
            Embedding.embedding_model == embedding_model,
        )
        .order_by(Story.external_id)
    ).all()

    if not rows:
        return

    stories = [row[0] for row in rows]
    vectors = np.array([row[1] for row in rows])
    texts = tuple(s.story_text for s in stories)
    k = max(1, min(dataset.default_cluster_k, len(stories)))

    labels, cluster_names = cluster_stories(vectors, texts, k)

    cluster_run_id = uuid.uuid4()
    cluster_by_label: dict[int, Cluster] = {}
    for label in sorted(set(labels)):
        mask = labels == label
        previews = [make_preview(text) for text, is_member in zip(texts, mask) if is_member]
        cluster_df = pd.DataFrame({"preview": previews})
        cluster = Cluster(
            dataset_id=dataset.id,
            embedding_model=embedding_model,
            cluster_run_id=cluster_run_id,
            cluster_label=int(label),
            theme_name=cluster_names[int(label)],
            summary=summarize_cluster(cluster_df, cluster_names[int(label)]),
            summary_source="rule_based",
        )
        session.add(cluster)
        cluster_by_label[int(label)] = cluster
    session.flush()

    for story, label in zip(stories, labels):
        session.add(
            ClusterAssignment(
                cluster_run_id=cluster_run_id,
                story_id=story.id,
                cluster_id=cluster_by_label[int(label)].id,
            )
        )
    session.commit()
