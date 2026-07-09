import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from src.embeddings import embed_texts


def semantic_scores(query: str, embeddings: np.ndarray, provider: str = "Local MiniLM") -> np.ndarray:
    query_embedding = embed_texts([query], provider)
    return cosine_similarity(query_embedding, embeddings).ravel()


def rank_by_scores(df: pd.DataFrame, scores: np.ndarray, top_k: int) -> pd.DataFrame:
    if len(df) != len(scores):
        raise ValueError("Dataframe length must match score length.")
    return df.assign(score=scores).sort_values("score", ascending=False).head(top_k)


def search(query: str, df: pd.DataFrame, embeddings: np.ndarray, top_k: int, provider: str = "Local MiniLM") -> pd.DataFrame:
    scores = semantic_scores(query, embeddings, provider)
    return rank_by_scores(df, scores, top_k)
