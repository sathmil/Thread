def test_list_stories_returns_seeded_dataset(client):
    response = client.get("/stories")

    assert response.status_code == 200
    stories = response.json()
    assert len(stories) == 10
    assert {"external_id", "title", "focus", "word_count", "preview"}.issubset(stories[0].keys())
    assert {s["external_id"] for s in stories} == {f"{i:03d}" for i in range(1, 11)}
