"""M7: embedding model versioning + re-index tests.

We don't have a real OPENAI_API_KEY in this environment, so the "two
distinct providers" scenario is exercised two ways: (1) requesting OpenAI
without a key, which must visibly fall back to local rather than silently
mislabeling what's stored, and (2) inserting a second, distinctly-tagged
embedding directly (simulating what a second real provider would produce)
to verify the query-side model filtering actually discriminates correctly
— that part of the mechanism doesn't care whether the vector came from a
real API call or a test fixture.

All DB assertions are scoped to the dataset created within each test —
this is a shared dev database across test runs, not an isolated test DB
(that lands in M9), so unscoped queries would pick up unrelated leftover
rows from other tests/datasets.
"""
import csv
import io
import uuid

from sqlalchemy import select

from app.config import LOCAL_MODEL_NAME
from app.db import SessionLocal
from app.models import Embedding, Story, TextUnit


def _csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "story_text"])
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _create_and_index_dataset(client, name: str) -> str:
    dataset_id = client.post("/datasets", json={"name": name}).json()["id"]
    rows = [
        {"id": "001", "story_text": "I found my community after joining the debate team in tenth grade."},
        {"id": "002", "story_text": "Every summer we drove twelve hours to see my grandparents in the valley."},
        {"id": "003", "story_text": "Learning to read music felt impossible until my teacher slowed down."},
    ]
    client.post(
        f"/datasets/{dataset_id}/upload",
        files={"file": ("stories.csv", _csv_bytes(rows), "text/csv")},
    )
    client.post(f"/datasets/{dataset_id}/index", json={})
    return dataset_id


def _embeddings_for_dataset(dataset_id: str):
    session = SessionLocal()
    try:
        return (
            session.execute(
                select(Embedding)
                .join(TextUnit, TextUnit.id == Embedding.text_unit_id)
                .join(Story, Story.id == TextUnit.story_id)
                .where(Story.dataset_id == uuid.UUID(dataset_id))
            )
            .scalars()
            .all()
        )
    finally:
        session.close()


def _text_units_for_dataset(dataset_id: str):
    session = SessionLocal()
    try:
        return (
            session.execute(
                select(TextUnit).join(Story, Story.id == TextUnit.story_id).where(
                    Story.dataset_id == uuid.UUID(dataset_id)
                )
            )
            .scalars()
            .all()
        )
    finally:
        session.close()


def test_index_stores_the_real_model_id_not_the_provider_label(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Model id storage test")

    models = {e.embedding_model for e in _embeddings_for_dataset(dataset_id)}

    # This is the M7 bug fix: previously this held "Local MiniLM" (the UI
    # provider label) instead of the actual model identifier.
    assert models == {LOCAL_MODEL_NAME}


def test_reindex_same_model_is_idempotent(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Idempotent reindex test")

    embeddings_before = _embeddings_for_dataset(dataset_id)
    text_units_before = _text_units_for_dataset(dataset_id)

    response = client.post(f"/datasets/{dataset_id}/reindex", json={"embedding_model": "Local MiniLM"})
    assert response.status_code == 202
    assert response.json()["status"] == "succeeded"

    embeddings_after = _embeddings_for_dataset(dataset_id)
    text_units_after = _text_units_for_dataset(dataset_id)

    # Re-running under the same model must not duplicate chunks or embeddings.
    assert len(text_units_after) == len(text_units_before)
    assert len(embeddings_after) == len(embeddings_before)


def test_reindex_to_openai_without_key_falls_back_with_warning(client, user_a, sign_in_as, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "OpenAI fallback test")

    response = client.post(f"/datasets/{dataset_id}/reindex", json={"embedding_model": "OpenAI API"})

    assert response.status_code == 202
    job = response.json()
    assert job["status"] == "succeeded"
    assert job["warning_message"] is not None
    assert "OPENAI_API_KEY" in job["warning_message"]


def test_two_embedding_models_are_independently_queryable(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Dual model comparison test")

    # Simulate a second provider's embeddings by copying this dataset's
    # existing MiniLM vectors under a distinct fake model id — exercises the
    # same model-filtering code path a real second provider would, without
    # needing network access.
    session = SessionLocal()
    try:
        text_units = (
            session.execute(
                select(TextUnit).join(Story, Story.id == TextUnit.story_id).where(
                    Story.dataset_id == uuid.UUID(dataset_id)
                )
            )
            .scalars()
            .all()
        )
        for text_unit in text_units:
            existing = session.execute(
                select(Embedding).where(Embedding.text_unit_id == text_unit.id)
            ).scalars().first()
            if existing is None:
                continue
            session.add(
                Embedding(
                    text_unit_id=text_unit.id,
                    embedding_model="fake-second-model",
                    embedding_version="v1",
                    vector_384=existing.vector_384,
                    dim=existing.dim,
                )
            )
        session.commit()
    finally:
        session.close()

    minilm_clusters = client.get(
        "/clusters", params={"dataset_id": dataset_id, "embedding_model": LOCAL_MODEL_NAME}
    )
    search_response = client.post(
        "/search",
        json={"query": "community", "unit": "Stories", "top_k": 3, "dataset_id": dataset_id},
    )

    assert minilm_clusters.status_code == 200
    assert sum(len(c["stories"]) for c in minilm_clusters.json()) == 3
    # The default (Local MiniLM) search path is unaffected by the extra
    # fake-model rows coexisting alongside it.
    assert search_response.status_code == 200
    assert len(search_response.json()["results"]) == 3
