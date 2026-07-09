import numpy as np
import pandas as pd
import pytest

from src.evaluation import evaluate_queries, parse_expected_ids


def test_parse_expected_ids_normalizes_ids():
    assert parse_expected_ids("1|002| 3 ") == {"001", "002", "003"}


def test_evaluate_queries_with_mocked_scores(monkeypatch):
    gold = pd.DataFrame({"query": ["voice"], "expected_story_ids": ["002"]})
    units = pd.DataFrame(
        {
            "id": ["001", "002"],
            "theme": ["A", "B"],
            "preview": ["first", "second"],
        }
    )
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)

    monkeypatch.setattr("src.evaluation.semantic_scores", lambda query, emb, provider: np.array([0.1, 0.9]))

    results, metrics = evaluate_queries(gold, units, embeddings, top_k=1)

    assert results.iloc[0]["top_story"] == "002"
    assert results.iloc[0]["hit_at_k"] == True
    assert metrics["recall@1"] == pytest.approx(1.0)
    assert metrics["mrr"] == pytest.approx(1.0)
