from pathlib import Path

import numpy as np
import pandas as pd

from app.config import EVALUATION_GOLD_PATH
from app.search import rank_by_scores, semantic_scores


def load_gold(path: Path = EVALUATION_GOLD_PATH) -> pd.DataFrame:
    gold = pd.read_csv(path)
    gold["expected_story_ids"] = gold["expected_story_ids"].astype(str)
    return gold


def parse_expected_ids(value: str) -> set[str]:
    return {item.strip().zfill(3) for item in str(value).split("|") if item.strip()}


def evaluate_queries(
    gold: pd.DataFrame,
    units_df: pd.DataFrame,
    unit_embeddings: np.ndarray,
    provider: str = "Local MiniLM",
    top_k: int = 3,
) -> tuple[pd.DataFrame, dict[str, float]]:
    rows = []
    reciprocal_ranks = []
    recall_hits = []

    for _, gold_row in gold.iterrows():
        query = gold_row["query"]
        expected_ids = parse_expected_ids(gold_row["expected_story_ids"])
        scores = semantic_scores(query, unit_embeddings, provider)
        ranked = rank_by_scores(units_df, scores, top_k=max(top_k, len(units_df)))
        ranked_ids = ranked["id"].astype(str).str.zfill(3).tolist()

        first_rank = next((idx + 1 for idx, story_id in enumerate(ranked_ids) if story_id in expected_ids), None)
        top_ids = ranked_ids[:top_k]
        hit = any(story_id in expected_ids for story_id in top_ids)

        reciprocal_ranks.append(1 / first_rank if first_rank else 0)
        recall_hits.append(1 if hit else 0)

        best = ranked.iloc[0]
        rows.append(
            {
                "query": query,
                "expected_story_ids": "|".join(sorted(expected_ids)),
                "top_story": best["id"],
                "top_theme": best.get("theme", ""),
                "score": round(float(best["score"]), 3),
                "hit_at_k": hit,
                "reciprocal_rank": round(1 / first_rank, 3) if first_rank else 0,
                "match": best["preview"],
            }
        )

    metrics = {
        f"recall@{top_k}": float(np.mean(recall_hits)) if recall_hits else 0.0,
        "mrr": float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0,
    }
    return pd.DataFrame(rows), metrics
