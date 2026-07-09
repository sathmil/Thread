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


def test_projection_covers_all_seeded_stories_with_2d_coordinates(client):
    response = client.get("/clusters/projection")

    assert response.status_code == 200
    points = response.json()
    assert len(points) == 10

    external_ids = {p["external_id"] for p in points}
    assert external_ids == {f"{i:03d}" for i in range(1, 11)}

    for point in points:
        assert isinstance(point["x"], float)
        assert isinstance(point["y"], float)
        assert point["cluster_label"] is not None
        assert point["theme_name"]
