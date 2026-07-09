import pytest


def test_evaluation_run_matches_known_metrics(client):
    response = client.get("/evaluation/run", params={"unit": "Passages", "top_k": 3})

    assert response.status_code == 200
    body = response.json()

    assert len(body["results"]) == 7
    assert body["recall_at_k"] == pytest.approx(0.857, abs=0.01)
    assert body["mrr"] == pytest.approx(0.893, abs=0.01)
