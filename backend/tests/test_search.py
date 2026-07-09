import numpy as np
import pandas as pd
import pytest

from app.search import rank_by_scores


def test_rank_by_scores_sorts_descending_and_limits_results():
    df = pd.DataFrame({"id": ["001", "002", "003"]})
    scores = np.array([0.1, 0.9, 0.3])

    ranked = rank_by_scores(df, scores, top_k=2)

    assert ranked["id"].tolist() == ["002", "003"]
    assert ranked["score"].tolist() == [0.9, 0.3]


def test_rank_by_scores_validates_lengths():
    df = pd.DataFrame({"id": ["001", "002"]})

    with pytest.raises(ValueError):
        rank_by_scores(df, np.array([0.1]), top_k=1)
