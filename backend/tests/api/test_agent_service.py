"""M8.7: the conversational agent's tool surface. No OpenAI key is
available in this environment, so these exercise the tool-dispatch logic
directly (the part that's fully testable without a live model) and the
answer_query() fallback path — the guaranteed path for anyone without a
key configured.
"""
import csv
import io
import uuid

from app.db import SessionLocal
from app.models import Dataset
from app.services import agent_service


def _csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "story_text"])
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _create_and_index_dataset(client, name: str) -> str:
    dataset_id = client.post("/datasets", json={"name": name}).json()["id"]
    rows = [
        {"id": "001", "story_text": "I found my community after joining the debate team and speaking up for myself."},
        {"id": "002", "story_text": "My grandmother taught me about our family and where we belong."},
        {"id": "003", "story_text": "After the loss, I grieved quietly, but slowly found hope again."},
    ]
    client.post(
        f"/datasets/{dataset_id}/upload",
        files={"file": ("stories.csv", _csv_bytes(rows), "text/csv")},
    )
    client.post(f"/datasets/{dataset_id}/index", json={})
    return dataset_id


def _open_dataset(dataset_id: str):
    session = SessionLocal()
    dataset = session.get(Dataset, uuid.UUID(dataset_id))
    return session, dataset


def test_tool_search_stories_returns_grounded_results(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Agent search tool test")
    session, dataset = _open_dataset(dataset_id)
    try:
        result = agent_service.dispatch_tool(
            session, dataset, "search_stories", {"query": "family and belonging", "top_k": 3}
        )
    finally:
        session.close()

    assert "results" in result
    assert len(result["results"]) > 0
    assert all({"story_id", "preview", "score"} <= r.keys() for r in result["results"])


def test_tool_filter_by_dimension_only_returns_scores_above_threshold(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Agent filter tool test")
    session, dataset = _open_dataset(dataset_id)
    try:
        result = agent_service.dispatch_tool(
            session, dataset, "filter_by_dimension", {"dimension": "family", "min_score": 0.1, "top_k": 5}
        )
    finally:
        session.close()

    assert result["dimension"] == "family"
    assert all(m["score"] >= 0.1 for m in result["matches"])


def test_tool_filter_by_dimension_rejects_unknown_dimension(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Agent filter tool invalid dimension test")
    session, dataset = _open_dataset(dataset_id)
    try:
        result = agent_service.dispatch_tool(session, dataset, "filter_by_dimension", {"dimension": "nonsense"})
    finally:
        session.close()

    assert "error" in result


def test_tool_describe_theme_finds_a_matching_cluster(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Agent describe theme tool test")
    session, dataset = _open_dataset(dataset_id)
    try:
        result = agent_service.dispatch_tool(session, dataset, "describe_theme", {"theme": "0"})
    finally:
        session.close()

    assert "error" not in result
    assert result["story_count"] >= 1
    assert result["sample_story_ids"]


def test_tool_compare_stories_explains_two_known_stories(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Agent compare tool test")
    session, dataset = _open_dataset(dataset_id)
    try:
        result = agent_service.dispatch_tool(
            session, dataset, "compare_stories", {"story_id_a": "001", "story_id_b": "002"}
        )
    finally:
        session.close()

    assert result["story_id_a"] == "001"
    assert result["story_id_b"] == "002"
    assert result["explanation"]


def test_tool_compare_stories_errors_on_unknown_story_id(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Agent compare tool unknown id test")
    session, dataset = _open_dataset(dataset_id)
    try:
        result = agent_service.dispatch_tool(
            session, dataset, "compare_stories", {"story_id_a": "001", "story_id_b": "does-not-exist"}
        )
    finally:
        session.close()

    assert "error" in result


def test_dispatch_tool_rejects_unknown_tool_name(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Agent unknown tool test")
    session, dataset = _open_dataset(dataset_id)
    try:
        result = agent_service.dispatch_tool(session, dataset, "delete_everything", {})
    finally:
        session.close()

    assert "error" in result


def test_answer_query_returns_fallback_message_without_openai_key(client, user_a, sign_in_as, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Agent fallback test")
    session, dataset = _open_dataset(dataset_id)
    try:
        result = agent_service.answer_query(session, dataset, "What themes are here?")
    finally:
        session.close()

    assert result.available is False
    assert "OpenAI" in result.answer
    assert result.tool_calls == []
