"""M8: Precision@K and the historical/model-comparison evaluation routes.
Uses a hand-verifiable 2-story dataset with one gold query expecting a
single story, so Precision@K's value can be checked by hand rather than
just asserted to exist.
"""
import csv
import io
import uuid

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Dataset, EvaluationQuery, EvaluationQueryExpectedStory, Story
from app.services import evaluation_service


def _csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "story_text"])
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _create_indexed_dataset_with_gold_query(client, name: str) -> tuple[str, str]:
    dataset_id = client.post("/datasets", json={"name": name}).json()["id"]
    rows = [
        {"id": "001", "story_text": "A story about finding belonging in a new school community."},
        {"id": "002", "story_text": "A story about grieving the loss of a grandmother and finding hope."},
    ]
    client.post(
        f"/datasets/{dataset_id}/upload",
        files={"file": ("stories.csv", _csv_bytes(rows), "text/csv")},
    )
    client.post(f"/datasets/{dataset_id}/index", json={})

    session = SessionLocal()
    try:
        dataset = session.get(Dataset, uuid.UUID(dataset_id))
        story_001 = session.execute(
            select(Story).where(Story.dataset_id == dataset.id, Story.external_id == "001")
        ).scalar_one()

        query = EvaluationQuery(dataset_id=dataset.id, query_text="belonging in a new school community")
        session.add(query)
        session.flush()
        session.add(EvaluationQueryExpectedStory(evaluation_query_id=query.id, story_id=story_001.id))
        session.commit()
        story_001_id = str(story_001.id)
    finally:
        session.close()

    return dataset_id, story_001_id


def test_precision_at_k_counts_only_truly_expected_hits(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id, _ = _create_indexed_dataset_with_gold_query(client, "Precision@K test")

    session = SessionLocal()
    try:
        dataset = session.get(Dataset, uuid.UUID(dataset_id))
        # Both stories are necessarily retrieved (only 2 exist) at top_k=2,
        # and exactly 1 of them is expected -> precision@2 = 1/2 = 0.5.
        run = evaluation_service.run_evaluation(session, dataset, unit="Stories", top_k=2, provider="Local MiniLM")
        precision_at_k = run.precision_at_k
    finally:
        session.close()

    assert precision_at_k == pytest.approx(0.5, abs=0.01)


def test_evaluation_run_route_surfaces_precision_at_k(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id, _ = _create_indexed_dataset_with_gold_query(client, "Precision@K route test")

    response = client.get(
        "/evaluation/run", params={"dataset_id": dataset_id, "unit": "Stories", "top_k": 2}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["precision_at_k"] == pytest.approx(0.5, abs=0.01)
    assert body["created_at"]


def test_run_mislabeled_as_openai_falls_back_to_the_model_actually_used(client, user_a, sign_in_as, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    sign_in_as(user_a)
    dataset_id, _ = _create_indexed_dataset_with_gold_query(client, "Provider fallback labeling test")

    response = client.get(
        "/evaluation/run",
        params={"dataset_id": dataset_id, "unit": "Stories", "top_k": 2, "embedding_model": "OpenAI API"},
    )

    assert response.status_code == 200
    # Without a key, the run actually queried Local MiniLM embeddings, so the
    # persisted/reported label should say so rather than claim "OpenAI API".
    assert response.json()["embedding_model"] == "Local MiniLM"


def test_list_runs_returns_history_without_full_per_query_detail(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id, _ = _create_indexed_dataset_with_gold_query(client, "History list test")

    client.get("/evaluation/run", params={"dataset_id": dataset_id, "unit": "Stories", "top_k": 2})
    client.get("/evaluation/run", params={"dataset_id": dataset_id, "unit": "Stories", "top_k": 2})

    response = client.get("/evaluation/runs", params={"dataset_id": dataset_id})

    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 2
    assert all(run["embedding_model"] == "Local MiniLM" for run in runs)
    assert all("results" not in run for run in runs)


def test_get_run_detail_requires_dataset_scoping(client, user_a, user_b, sign_in_as):
    sign_in_as(user_a)
    dataset_id, _ = _create_indexed_dataset_with_gold_query(client, "History detail scoping test")

    run_id = client.get(
        "/evaluation/run", params={"dataset_id": dataset_id, "unit": "Stories", "top_k": 2}
    ).json()["run_id"]

    detail = client.get(f"/evaluation/runs/{run_id}")
    assert detail.status_code == 200
    assert len(detail.json()["results"]) == 1

    sign_in_as(user_b)
    forbidden = client.get(f"/evaluation/runs/{run_id}")
    assert forbidden.status_code == 403


def test_get_run_detail_404_for_unknown_run(client, user_a, sign_in_as):
    sign_in_as(user_a)
    response = client.get(f"/evaluation/runs/{uuid.uuid4()}")
    assert response.status_code == 404
