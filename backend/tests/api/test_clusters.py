def test_clusters_cover_all_seeded_stories(client):
    response = client.get("/clusters")

    assert response.status_code == 200
    clusters = response.json()
    assert len(clusters) == 3

    total_stories = sum(len(c["stories"]) for c in clusters)
    assert total_stories == 10

    for cluster in clusters:
        assert cluster["theme_name"]
        assert cluster["summary"]
        assert cluster["summary_source"] == "rule_based"
