import numpy as np

from app.clustering import cluster_stories, project_embeddings, reorder_labels_by_size, top_terms


def test_reorder_labels_by_size_makes_largest_cluster_zero():
    labels = np.array([5, 5, 2, 5, 2, 9])

    reordered = reorder_labels_by_size(labels)

    assert reordered.tolist().count(0) == 3
    assert set(reordered.tolist()) == {0, 1, 2}


def test_top_terms_returns_readable_label():
    label = top_terms(["school library books", "school teacher books"], limit=2)

    assert isinstance(label, str)
    assert label


def test_cluster_stories_returns_expected_number_of_labels_and_names():
    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.9, 0.1],
            [0.0, 1.0],
            [0.1, 0.9],
        ],
        dtype=np.float32,
    )
    texts = ("voice story", "voice speech", "school books", "school library")

    labels, names = cluster_stories(embeddings, texts, n_clusters=2)

    assert len(labels) == 4
    assert set(labels.tolist()) == {0, 1}
    assert set(names.keys()) == {0, 1}


def test_project_embeddings_returns_two_dimensions():
    embeddings = np.eye(3, dtype=np.float32)

    coords = project_embeddings(embeddings)

    assert coords.shape == (3, 2)
