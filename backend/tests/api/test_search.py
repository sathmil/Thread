import pytest


def test_search_ranks_expected_passage_first(client):
    response = client.post(
        "/search",
        json={"query": "feeling invisible at school", "unit": "Passages", "top_k": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"], "expected at least one result"

    top = body["results"][0]
    assert top["story_id"] == "002"
    assert top["score"] == pytest.approx(0.560, abs=0.01)


def test_search_rejects_unknown_unit(client):
    response = client.post("/search", json={"query": "voice", "unit": "Paragraphs", "top_k": 3})

    assert response.status_code == 422
