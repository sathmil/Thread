import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clustering import cluster_stories
from app.embeddings import embed_texts
from app.models import Cluster, ClusterAssignment, Dataset, Embedding, Story, TextUnit
from app.services import fingerprint_service, theme_report_service
from app.services.embedding_columns import model_id_for_provider, resolve_provider, vector_column, vector_kwargs
from app.text import make_preview, split_text_units

UNIT_LABEL_TO_TYPE = {"Sentences": "sentence", "Passages": "passage", "Stories": "story"}

# Safeguard against pathological unit counts on very long stories — caps
# how many sentence/passage units a single story can contribute.
MAX_UNITS_PER_STORY = {"sentence": 200, "passage": 60, "story": 1}

# Below this many stories, POST /datasets/{id}/index (and /reindex) run
# synchronously in the request for a snappier UX; at or above it, indexing
# always goes through Celery (roadmap M6 design decision).
SYNC_INDEX_THRESHOLD = 25

# Above this many stories, clustering is dispatched as its own chained
# Celery task rather than run inline at the end of indexing.
ASYNC_CLUSTER_THRESHOLD = 25

# Stories per embedding batch — keeps progress reporting granular (and
# commits incrementally) regardless of dataset size, instead of one giant
# embed_texts() call per unit type with no visible movement in between.
STORY_BATCH_SIZE = 20

EMBEDDING_VERSION = "v1"


@dataclass
class IndexResult:
    story_count: int
    embedding_ms: float
    actual_embedding_model: str
    warning: str | None


def index_dataset(
    session: Session,
    dataset: Dataset,
    embedding_model: str = "Local MiniLM",
    on_progress: Callable[[int], None] | None = None,
) -> IndexResult:
    """Chunks + embeds every story in the dataset, in batches. Idempotent:
    reuses existing TextUnit rows (chunking doesn't depend on the embedding
    model) and only adds Embedding rows for (text_unit, model, version)
    combinations that don't exist yet. That's what makes calling this again
    under a different embedding_model (re-indexing) safe — it neither
    violates the (story_id, unit_type, unit_index) unique constraint on
    TextUnit nor deletes the previous model's embeddings; old and new
    coexist for comparison, per the roadmap's M7 design.
    """
    actual_model, warning = resolve_provider(embedding_model)
    model_id = model_id_for_provider(actual_model)

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

            existing_by_story: dict[uuid.UUID, list[TextUnit]] = {}
            if batch:
                existing_rows = (
                    session.execute(
                        select(TextUnit).where(
                            TextUnit.story_id.in_([s.id for s in batch]),
                            TextUnit.unit_type == unit_type,
                        )
                    )
                    .scalars()
                    .all()
                )
                for text_unit in existing_rows:
                    existing_by_story.setdefault(text_unit.story_id, []).append(text_unit)

            batch_text_units: list[TextUnit] = []
            for story in batch:
                existing = existing_by_story.get(story.id)
                if existing:
                    batch_text_units.extend(existing)
                    continue
                parts = split_text_units(story.story_text, unit_label)[:cap]
                for unit_index, part in enumerate(parts, start=1):
                    text_unit = TextUnit(
                        story_id=story.id,
                        unit_type=unit_type,
                        unit_index=unit_index,
                        text_unit=part,
                        preview=make_preview(part, limit=260),
                    )
                    session.add(text_unit)
                    batch_text_units.append(text_unit)
            session.flush()

            if batch_text_units:
                already_embedded_ids = set(
                    session.execute(
                        select(Embedding.text_unit_id).where(
                            Embedding.text_unit_id.in_([tu.id for tu in batch_text_units]),
                            Embedding.embedding_model == model_id,
                            Embedding.embedding_version == EMBEDDING_VERSION,
                        )
                    )
                    .scalars()
                    .all()
                )
                to_embed = [tu for tu in batch_text_units if tu.id not in already_embedded_ids]

                if to_embed:
                    start = time.perf_counter()
                    vectors = embed_texts([tu.text_unit for tu in to_embed], actual_model)
                    embedding_ms_total += (time.perf_counter() - start) * 1000

                    for text_unit, vector in zip(to_embed, vectors):
                        session.add(
                            Embedding(
                                text_unit_id=text_unit.id,
                                embedding_model=model_id,
                                embedding_version=EMBEDDING_VERSION,
                                **vector_kwargs(vector),
                            )
                        )
                session.commit()

            completed_batches += 1
            if on_progress:
                on_progress(min(90, int(completed_batches / total_batches * 90)))

    return IndexResult(
        story_count=len(stories),
        embedding_ms=embedding_ms_total,
        actual_embedding_model=actual_model,
        warning=warning,
    )


def cluster_dataset(session: Session, dataset: Dataset, embedding_model: str = "Local MiniLM") -> None:
    """KMeans over whole-story embeddings, re-queried from the DB (rather than
    passed in-memory) so this can run standalone as its own Celery task,
    independent from whichever process ran index_dataset(). Takes a
    provider label (like index_dataset) and converts to the stored model id
    internally — callers never need to think about the distinction.
    """
    model_id = model_id_for_provider(embedding_model)
    column = vector_column(embedding_model)
    rows = session.execute(
        select(Story, column)
        .select_from(Story)
        .join(TextUnit, TextUnit.story_id == Story.id)
        .join(Embedding, Embedding.text_unit_id == TextUnit.id)
        .where(
            Story.dataset_id == dataset.id,
            TextUnit.unit_type == "story",
            Embedding.embedding_model == model_id,
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
        member_stories = [s for s, is_member in zip(stories, mask) if is_member]
        previews = [make_preview(s.story_text) for s in member_stories]
        cluster_df = pd.DataFrame({"preview": previews})
        theme_name = cluster_names[int(label)]

        fingerprints = [
            fingerprint_service.compute_fingerprint(session, s).dimensions for s in member_stories
        ]
        summary, summary_source = theme_report_service.generate_report(cluster_df, theme_name, fingerprints)

        cluster = Cluster(
            dataset_id=dataset.id,
            embedding_model=model_id,
            cluster_run_id=cluster_run_id,
            cluster_label=int(label),
            theme_name=theme_name,
            summary=summary,
            summary_source=summary_source,
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
