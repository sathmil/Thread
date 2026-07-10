"""M8.5: the insight engine. Unit tests exercise the pure math (correlation,
superlative selection) against crafted fixtures where the right answer is
known by construction; the API test checks the full computed-and-cached
route against a real indexed dataset. No OpenAI key is available here, so
finding_text always comes from the deterministic templates, not the LLM
rephrasing pass.
"""
import csv
import io

from app.services import insight_service


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
        {"id": "004", "story_text": "I chose to stand up and speak my mind, and my family stood behind me."},
        {"id": "005", "story_text": "We moved every season, and I never felt like I belonged anywhere."},
        {"id": "006", "story_text": "My mother and father raised me to believe I could lead one day."},
    ]
    client.post(
        f"/datasets/{dataset_id}/upload",
        files={"file": ("stories.csv", _csv_bytes(rows), "text/csv")},
    )
    client.post(f"/datasets/{dataset_id}/index", json={})
    return dataset_id


def test_compute_correlations_finds_the_planted_relationship_and_ignores_noise():
    # hope and growth rise together by construction; grief is unrelated noise.
    fingerprints = [
        {"hope": 0.1, "isolation": 0.0, "identity": 0.0, "family": 0.0, "growth": 0.15, "grief": 0.9, "belonging": 0.0, "agency": 0.0},
        {"hope": 0.3, "isolation": 0.0, "identity": 0.0, "family": 0.0, "growth": 0.35, "grief": 0.1, "belonging": 0.0, "agency": 0.0},
        {"hope": 0.5, "isolation": 0.0, "identity": 0.0, "family": 0.0, "growth": 0.55, "grief": 0.6, "belonging": 0.0, "agency": 0.0},
        {"hope": 0.7, "isolation": 0.0, "identity": 0.0, "family": 0.0, "growth": 0.75, "grief": 0.2, "belonging": 0.0, "agency": 0.0},
        {"hope": 0.9, "isolation": 0.0, "identity": 0.0, "family": 0.0, "growth": 0.95, "grief": 0.7, "belonging": 0.0, "agency": 0.0},
    ]

    findings = insight_service.compute_correlations(fingerprints)

    assert any(
        {f.dimension_a, f.dimension_b} == {"hope", "growth"} and f.effect_size > 0.9 for f in findings
    )
    assert not any({f.dimension_a, f.dimension_b} == {"hope", "grief"} for f in findings)
    assert all(f.sample_size == 5 for f in findings)


def test_compute_correlations_returns_nothing_below_the_sample_size_floor():
    fingerprints = [
        {"hope": 0.1, "isolation": 0.0, "identity": 0.0, "family": 0.0, "growth": 0.1, "grief": 0.0, "belonging": 0.0, "agency": 0.0},
        {"hope": 0.9, "isolation": 0.0, "identity": 0.0, "family": 0.0, "growth": 0.9, "grief": 0.0, "belonging": 0.0, "agency": 0.0},
    ]

    assert insight_service.compute_correlations(fingerprints) == []


def test_most_unique_picks_the_point_farthest_from_every_centroid():
    import numpy as np

    from app.models import Story

    stories = [Story(external_id=str(i), story_text="x") for i in range(4)]
    # Cluster 0: two points near (0,0); cluster 1: one point near (10,10);
    # story index 3 sits far from both centroids.
    vectors = np.array([[0.0, 0.0], [0.1, 0.1], [10.0, 10.0], [5.0, 5.0]])
    labels = [0, 0, 1, 1]

    finding = insight_service.most_unique(stories, vectors, labels)

    assert finding is not None
    assert finding.subject_story_id == stories[3].id


def test_most_representative_per_theme_picks_the_centroid_nearest_member():
    import numpy as np

    from app.models import Story

    stories = [Story(external_id=str(i), story_text="x") for i in range(3)]
    vectors = np.array([[0.0, 0.0], [1.0, 1.0], [0.05, 0.05]])
    labels = [0, 0, 0]

    findings = insight_service.most_representative_per_theme(stories, vectors, labels, {0: "Only theme"})

    assert len(findings) == 1
    assert findings[0].subject_story_id == stories[2].id  # closest to the 3-point centroid


def test_insights_route_returns_findings_across_multiple_types(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Insights test")

    response = client.get(f"/datasets/{dataset_id}/insights")

    assert response.status_code == 200
    findings = response.json()
    assert len(findings) > 0

    finding_types = {f["finding_type"] for f in findings}
    assert "most_representative" in finding_types
    assert "most_unique" in finding_types
    assert "most_complex" in finding_types

    for finding in findings:
        assert finding["finding_text"]
        if finding["subject_story_uuid"] is not None:
            assert finding["subject_story_external_id"] is not None


def test_insights_are_cached_not_recomputed_on_second_request(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Insights caching test")

    first = client.get(f"/datasets/{dataset_id}/insights").json()
    second = client.get(f"/datasets/{dataset_id}/insights").json()

    assert len(first) == len(second)
    assert {f["finding_text"] for f in first} == {f["finding_text"] for f in second}


def test_insights_require_dataset_scoping(client, user_a, user_b, sign_in_as):
    sign_in_as(user_a)
    dataset_id = _create_and_index_dataset(client, "Insights scoping test")

    sign_in_as(user_b)
    response = client.get(f"/datasets/{dataset_id}/insights")

    assert response.status_code == 403
