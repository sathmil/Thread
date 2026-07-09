"""Seed the database with the 10-story WHO WE ARE dataset + gold evaluation queries.

Reuses the existing app.data/app.text/app.embeddings/app.clustering/app.evaluation
logic (the M1 goal is a persistence-layer change, not a logic rewrite). Safe to
re-run: it deletes and recreates the public seed dataset each time.
"""
import uuid

import numpy as np

from app.clustering import cluster_stories, summarize_cluster
from app.config import LOCAL_MODEL_NAME
from app.data import load_stories
from app.db import SessionLocal
from app.embeddings import embed_texts
from app.evaluation import load_gold, parse_expected_ids
from app.models import (
    Cluster,
    ClusterAssignment,
    Dataset,
    Embedding,
    EvaluationQuery,
    EvaluationQueryExpectedStory,
    Story,
    TextUnit,
)
from app.text import make_preview, split_text_units

SEED_DATASET_NAME = "WHO WE ARE (seed)"
UNIT_LABEL_TO_TYPE = {"Sentences": "sentence", "Passages": "passage", "Stories": "story"}
EMBEDDING_PROVIDER = "Local MiniLM"


def seed() -> None:
    session = SessionLocal()
    try:
        existing = session.query(Dataset).filter_by(name=SEED_DATASET_NAME).one_or_none()
        if existing is not None:
            session.delete(existing)
            session.commit()

        dataset = Dataset(
            owner_user_id=None,
            name=SEED_DATASET_NAME,
            description="The original 10-story WHO WE ARE prototype dataset, seeded as a public demo dataset.",
            visibility="public",
            status="indexing",
        )
        session.add(dataset)
        session.flush()

        stories_df = load_stories()
        story_by_external_id: dict[str, Story] = {}
        for _, row in stories_df.iterrows():
            story = Story(
                dataset_id=dataset.id,
                external_id=row["id"],
                title=row["title"],
                focus=row["focus"],
                story_text=row["story_text"],
                word_count=int(row["word_count"]),
                source=row["source"],
            )
            session.add(story)
            story_by_external_id[row["id"]] = story
        session.flush()

        story_level_embeddings_by_external_id: dict[str, list[float]] = {}

        for unit_label, unit_type in UNIT_LABEL_TO_TYPE.items():
            unit_texts: list[str] = []
            unit_refs: list[tuple[Story, int]] = []

            for _, row in stories_df.iterrows():
                story = story_by_external_id[row["id"]]
                parts = split_text_units(row["story_text"], unit_label)
                for unit_index, part in enumerate(parts, start=1):
                    unit_texts.append(part)
                    unit_refs.append((story, unit_index))

            vectors = embed_texts(unit_texts, EMBEDDING_PROVIDER)

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
                        embedding_model=LOCAL_MODEL_NAME,
                        embedding_version="v1",
                        vector_384=vector.tolist(),
                        dim=len(vector),
                    )
                )

                if unit_type == "story":
                    story_level_embeddings_by_external_id[story.external_id] = vector

        # Cluster on the whole-story embeddings, matching the original prototype's
        # story-level clustering (per-dataset, not global — see roadmap M1 note).
        ordered_external_ids = [row["id"] for _, row in stories_df.iterrows()]
        story_vectors = [story_level_embeddings_by_external_id[eid] for eid in ordered_external_ids]
        story_texts = tuple(stories_df["story_text"].tolist())

        labels, cluster_names = cluster_stories(np.array(story_vectors), story_texts, dataset.default_cluster_k)

        cluster_run_id = uuid.uuid4()
        cluster_by_label: dict[int, Cluster] = {}
        for label in sorted(set(labels)):
            mask = labels == label
            cluster_df = stories_df.loc[mask]
            cluster = Cluster(
                dataset_id=dataset.id,
                embedding_model=LOCAL_MODEL_NAME,
                cluster_run_id=cluster_run_id,
                cluster_label=int(label),
                theme_name=cluster_names[int(label)],
                summary=summarize_cluster(cluster_df, cluster_names[int(label)]),
                summary_source="rule_based",
            )
            session.add(cluster)
            cluster_by_label[int(label)] = cluster
        session.flush()

        for external_id, label in zip(ordered_external_ids, labels):
            session.add(
                ClusterAssignment(
                    cluster_run_id=cluster_run_id,
                    story_id=story_by_external_id[external_id].id,
                    cluster_id=cluster_by_label[int(label)].id,
                )
            )

        gold = load_gold()
        for _, row in gold.iterrows():
            query = EvaluationQuery(
                dataset_id=dataset.id,
                query_text=row["query"],
                rationale=row.get("rationale"),
            )
            session.add(query)
            session.flush()

            for expected_id in parse_expected_ids(row["expected_story_ids"]):
                story = story_by_external_id.get(expected_id)
                if story is None:
                    continue
                session.add(
                    EvaluationQueryExpectedStory(evaluation_query_id=query.id, story_id=story.id)
                )

        dataset.status = "ready"
        session.commit()

        print(f"Seeded dataset {dataset.id} ({SEED_DATASET_NAME!r}):")
        print(f"  {len(story_by_external_id)} stories")
        print(f"  {session.query(TextUnit).filter(TextUnit.story_id.in_([s.id for s in story_by_external_id.values()])).count()} text units")
        print(f"  {len(cluster_by_label)} clusters (run {cluster_run_id})")
        print(f"  {len(gold)} evaluation queries")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
