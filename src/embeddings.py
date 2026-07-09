import json
import os
import urllib.request
from pathlib import Path
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import HashingVectorizer

from src.config import EMBEDDINGS_PATH, LOCAL_MODEL_NAME, OPENAI_EMBEDDING_MODEL, OPENAI_EMBEDDINGS_PATH


@lru_cache(maxsize=2)
def load_model(model_name: str = LOCAL_MODEL_NAME) -> SentenceTransformer:
    return SentenceTransformer(model_name, local_files_only=True)


def normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    embeddings = np.asarray(embeddings, dtype=np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / np.maximum(norms, 1e-12)


def local_embed(texts: list[str], model: SentenceTransformer | None = None) -> np.ndarray:
    try:
        active_model = model or load_model()
        embeddings = active_model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(embeddings, dtype=np.float32)
    except Exception:
        return hashing_embed(texts)


def hashing_embed(texts: list[str], n_features: int = 384) -> np.ndarray:
    vectorizer = HashingVectorizer(
        n_features=n_features,
        alternate_sign=False,
        norm=None,
        ngram_range=(1, 2),
        stop_words="english",
    )
    matrix = vectorizer.transform(texts)
    return normalize_embeddings(matrix.toarray())


def openai_embed(texts: list[str], api_key: str, model_name: str = OPENAI_EMBEDDING_MODEL) -> np.ndarray:
    request = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=json.dumps({"model": model_name, "input": texts}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    embeddings = np.array([item["embedding"] for item in payload["data"]], dtype=np.float32)
    return normalize_embeddings(embeddings)


def embed_texts(texts: list[str], provider: str = "Local MiniLM") -> np.ndarray:
    if provider == "OpenAI API" and os.getenv("OPENAI_API_KEY"):
        return openai_embed(texts, os.environ["OPENAI_API_KEY"])
    return local_embed(texts)


def load_or_create_story_embeddings(
    stories: tuple[str, ...],
    provider: str = "Local MiniLM",
    local_path: Path = EMBEDDINGS_PATH,
    openai_path: Path = OPENAI_EMBEDDINGS_PATH,
) -> np.ndarray:
    path = openai_path if provider == "OpenAI API" else local_path
    if path.exists():
        embeddings = np.load(path)
        if len(embeddings) == len(stories):
            return embeddings

    embeddings = embed_texts(list(stories), provider)
    if provider != "OpenAI API" or os.getenv("OPENAI_API_KEY"):
        np.save(path, embeddings)
    return embeddings
