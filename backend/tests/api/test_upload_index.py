"""Job-flow integration tests for POST /datasets/{id}/upload -> /index ->
GET /jobs/{id}, covering both the sync (small dataset) and async (Celery,
run in eager mode via conftest's _celery_eager_mode) paths, plus the
max-units-per-story chunking safeguard.
"""
import csv
import io

from scripts.generate_synthetic_dataset import generate_synthetic_stories


def _csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "story_text"])
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _create_dataset(client, name: str) -> str:
    return client.post("/datasets", json={"name": name}).json()["id"]


def test_small_dataset_indexes_synchronously_and_becomes_searchable(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_dataset(client, "Small sync-indexed dataset")

    rows = [
        {"id": "001", "story_text": "I found my community after joining the debate team in tenth grade."},
        {"id": "002", "story_text": "Every summer we drove twelve hours to see my grandparents in the valley."},
        {"id": "003", "story_text": "Learning to read music felt impossible until my teacher slowed down."},
    ]
    upload_response = client.post(
        f"/datasets/{dataset_id}/upload",
        files={"file": ("stories.csv", _csv_bytes(rows), "text/csv")},
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["stories_created"] == 3

    index_response = client.post(f"/datasets/{dataset_id}/index", json={})
    assert index_response.status_code == 202
    job = index_response.json()
    assert job["status"] == "succeeded"
    assert job["story_count"] == 3
    assert job["progress_pct"] == 100
    assert job["duration_ms"] is not None

    job_status = client.get(f"/jobs/{job['id']}")
    assert job_status.status_code == 200
    assert job_status.json()["status"] == "succeeded"

    search_response = client.post(
        "/search",
        json={"query": "debate team community", "unit": "Stories", "top_k": 3, "dataset_id": dataset_id},
    )
    assert search_response.status_code == 200
    assert search_response.json()["results"][0]["story_id"] == "001"

    clusters_response = client.get("/clusters", params={"dataset_id": dataset_id})
    assert clusters_response.status_code == 200
    assert sum(len(c["stories"]) for c in clusters_response.json()) == 3


def test_large_dataset_dispatches_via_celery_and_chains_clustering(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_dataset(client, "Large async-indexed dataset")

    rows = generate_synthetic_stories(30)
    upload_response = client.post(
        f"/datasets/{dataset_id}/upload",
        files={"file": ("synthetic.csv", _csv_bytes(rows), "text/csv")},
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["stories_created"] == 30

    index_response = client.post(f"/datasets/{dataset_id}/index", json={})
    assert index_response.status_code == 202
    # Eager Celery mode runs the task (and its chained cluster_dataset_task)
    # synchronously during .delay(), so by the time the response comes back
    # the job has already completed.
    job = index_response.json()
    assert job["status"] == "succeeded"
    assert job["story_count"] == 30
    assert job["embedding_ms"] is not None
    assert job["avg_embedding_ms_per_story"] is not None

    clusters_response = client.get("/clusters", params={"dataset_id": dataset_id})
    assert clusters_response.status_code == 200
    assert sum(len(c["stories"]) for c in clusters_response.json()) == 30


def test_chunking_safeguard_caps_units_for_a_pathologically_long_story(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_dataset(client, "Pathological length dataset")

    huge_story = "This is one sentence. " * 500  # 500 sentences, far above the cap
    rows = [{"id": "001", "story_text": huge_story}]
    client.post(
        f"/datasets/{dataset_id}/upload",
        files={"file": ("huge.csv", _csv_bytes(rows), "text/csv")},
    )

    index_response = client.post(f"/datasets/{dataset_id}/index", json={})
    assert index_response.status_code == 202
    assert index_response.json()["status"] == "succeeded"

    search_response = client.post(
        "/search",
        json={"query": "sentence", "unit": "Sentences", "top_k": 1000, "dataset_id": dataset_id},
    )
    assert search_response.status_code == 200
    # MAX_UNITS_PER_STORY["sentence"] = 200 — the 500-sentence story must be
    # capped, not indexed in full.
    assert len(search_response.json()["results"]) <= 200


def test_index_requires_owner(client, user_a, user_b, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_dataset(client, "Owner-only dataset")

    sign_in_as(user_b)
    response = client.post(f"/datasets/{dataset_id}/index", json={})

    assert response.status_code == 403


def test_upload_requires_valid_csv_with_story_text_column(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_dataset(client, "Bad upload dataset")

    bad_csv = b"not_story_text\nhello\n"
    response = client.post(
        f"/datasets/{dataset_id}/upload",
        files={"file": ("bad.csv", bad_csv, "text/csv")},
    )

    assert response.status_code == 422
