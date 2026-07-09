import pandas as pd
import numpy as np

from src.clustering import cluster_stories
from src.data import load_stories
from src.embeddings import embed_texts, load_or_create_story_embeddings
from src.text import split_into_units


def build_story_index(cluster_count: int = 3, provider: str = "Local MiniLM") -> tuple[pd.DataFrame, np.ndarray, dict[int, str]]:
    df = load_stories()
    story_texts = tuple(df["story_text"].tolist())
    embeddings = load_or_create_story_embeddings(story_texts, provider)
    labels, cluster_names = cluster_stories(embeddings, story_texts, cluster_count)
    df = df.assign(cluster=labels)
    df["theme"] = df["cluster"].map(cluster_names)
    return df, embeddings, cluster_names


def build_unit_index(df: pd.DataFrame, unit: str, provider: str = "Local MiniLM"):
    unit_df = split_into_units(df, unit)
    unit_embeddings = embed_texts(unit_df["text_unit"].tolist(), provider)
    unit_df = unit_df.merge(df[["id", "cluster", "theme"]], on="id", how="left")
    return unit_df, unit_embeddings
