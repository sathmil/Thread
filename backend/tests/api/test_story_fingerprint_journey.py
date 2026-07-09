"""M7.5: narrative fingerprints, story journeys, and AI-synthesized theme
reports. No OpenAI key is available in this environment, so these verify
the deterministic fallback paths (which are the paths guaranteed to run
for anyone without a key configured) rather than real LLM output.
"""
import csv
import io
import uuid

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Story

FINGERPRINT_DIMENSIONS = {
    "hope",
    "isolation",
    "identity",
    "family",
    "growth",
    "grief",
    "belonging",
    "agency",
}


def _csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "story_text"])
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _create_and_index_dataset(client, name: str) -> str:
    dataset_id = client.post("/datasets", json={"name": name}).json()["id"]
    rows = [
        {
            "id": "001",
            "story_text": "I found my community after joining the debate team and speaking up for myself.",
        },
        {"id": "002", "story_text": "My grandmother taught me about our family and where we belong."},
        {"id": "003", "story_text": "After the loss, I grieved quietly, but slowly found hope again."},
    ]
    client.post(
        f"/datasets/{dataset_id}/upload",
        files={"file": ("stories.csv", _csv_bytes(rows), "text/csv")},
    )
    client.post(f"/datasets/{dataset_id}/index", json={})
    return dataset_id


def _story_uuid(dataset_id: str, external_id: str) -> str:
    session = SessionLocal()
    try:
        return str(
            session.execute(
                select(Story.id).where(
                    Story.dataset_id == uuid.UUID(dataset_id), Story.external_id == external_id
                )
            ).scalar_one()
        )
    finally:
        session.close()


def test_fingerprint_uses_keyword_fallback_and_is_cached(client, user_a, sign_in_as, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Fingerprint fallback test")
    story_id = _story_uuid(dataset_id, "001")

    first = client.get(f"/stories/{story_id}/fingerprint")
    assert first.status_code == 200
    body = first.json()
    assert body["source"] == "rule_based"
    assert body["model"] == "keyword-heuristic-v1"
    assert set(body["dimensions"].keys()) == FINGERPRINT_DIMENSIONS

    second = client.get(f"/stories/{story_id}/fingerprint")
    assert second.json()["dimensions"] == first.json()["dimensions"]


def test_journey_returns_nearest_contrasting_and_reflection_questions(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Journey test")
    story_id = _story_uuid(dataset_id, "001")

    response = client.get(f"/stories/{story_id}/journey")
    assert response.status_code == 200
    body = response.json()

    assert len(body["nearest"]) == 2  # the other 2 stories in this 3-story dataset
    assert body["contrasting"] is not None
    assert body["contrasting"]["story_id"] != "001"
    assert all(entry["story_id"] != "001" for entry in body["nearest"])
    assert len(body["reflection_questions"]) == 2
    assert all(entry["explanation"] for entry in body["nearest"])


def test_theme_reports_fall_back_to_rule_based_without_llm_key(client, user_a, sign_in_as, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Theme report fallback test")

    response = client.get("/clusters", params={"dataset_id": dataset_id})
    assert response.status_code == 200
    clusters = response.json()
    assert len(clusters) > 0
    for cluster in clusters:
        assert cluster["summary_source"] == "rule_based"
        assert cluster["summary"]


def test_story_detail_requires_dataset_scoping(client, user_a, user_b, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Scoped story detail test")
    story_id = _story_uuid(dataset_id, "001")

    sign_in_as(user_b)
    response = client.get(f"/stories/{story_id}")

    assert response.status_code == 403


def test_story_detail_404_for_unknown_story(client, user_a, sign_in_as):
    sign_in_as(user_a)
    response = client.get(f"/stories/{uuid.uuid4()}")

    assert response.status_code == 404
