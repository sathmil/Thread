"""M8.7's "mirror my story": unauthenticated, ad hoc, no dataset/account
required. Unlike /query, this doesn't need an OpenAI key to produce its
real result — embedding uses local MiniLM and fingerprint scoring falls
back to the deterministic keyword scorer — so this is the one M8.7
feature we can verify end-to-end rather than just its fallback path.
"""
import pytest

from app.routers import mirror


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    mirror._request_log.clear()
    yield
    mirror._request_log.clear()


def test_mirror_returns_matches_and_fingerprint_against_the_seed_dataset(client):
    response = client.post(
        "/mirror",
        json={
            "story_text": "I moved every year and never felt like I belonged, until my grandmother's stories gave me a sense of family again.",
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert len(body["matches"]) > 0
    assert len(body["matches"]) <= 3
    for match in body["matches"]:
        assert match["story_id"]
        assert match["explanation"]
        assert 0.0 <= match["score"] <= 1.0

    assert body["fingerprint_source"] in ("llm", "rule_based")
    assert set(body["fingerprint"].keys()) == {
        "hope", "isolation", "identity", "family", "growth", "grief", "belonging", "agency",
    }


def test_mirror_does_not_require_authentication(client):
    response = client.post("/mirror", json={"story_text": "A short story about starting over somewhere new."})

    assert response.status_code == 200


def test_mirror_is_rate_limited_per_client(client):
    for _ in range(mirror.RATE_LIMIT_MAX_REQUESTS):
        response = client.post("/mirror", json={"story_text": "A quick story for rate-limit testing."})
        assert response.status_code == 200

    limited = client.post("/mirror", json={"story_text": "One request too many."})
    assert limited.status_code == 429
