import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer

from app.config import FOCUS_SIGNALS


def reorder_labels_by_size(labels: np.ndarray) -> np.ndarray:
    counts = pd.Series(labels).value_counts().sort_values(ascending=False)
    mapping = {old_label: new_label for new_label, old_label in enumerate(counts.index)}
    return np.array([mapping[label] for label in labels])


def top_terms(texts: list[str], limit: int = 4) -> str:
    if not texts:
        return "Untitled theme"

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_features=80,
        )
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return "Untitled theme"

    scores = np.asarray(matrix.mean(axis=0)).ravel()
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(terms, scores), key=lambda item: item[1], reverse=True)

    clean_terms = []
    for term, _ in ranked:
        if len(term) < 3 or term in clean_terms:
            continue
        if any(term in existing or existing in term for existing in clean_terms):
            continue
        clean_terms.append(term)
        if len(clean_terms) == limit:
            break

    return ", ".join(clean_terms).title() if clean_terms else "Untitled theme"


def name_clusters(labels: np.ndarray, texts: tuple[str, ...]) -> dict[int, str]:
    names: dict[int, str] = {}
    for label in sorted(set(labels)):
        cluster_texts = [text for text, text_label in zip(texts, labels) if text_label == label]
        names[int(label)] = top_terms(cluster_texts)
    return names


def cluster_stories(embeddings: np.ndarray, texts: tuple[str, ...], n_clusters: int) -> tuple[np.ndarray, dict[int, str]]:
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
    labels = kmeans.fit_predict(embeddings)
    labels = reorder_labels_by_size(labels)
    names = name_clusters(labels, texts)
    return labels, names


def summarize_cluster(cluster_df: pd.DataFrame, theme: str) -> str:
    examples = cluster_df["preview"].tolist()
    if not examples:
        return "No stories are currently assigned to this theme."

    combined = " ".join(examples).lower()
    matched = [
        label
        for label, needles in FOCUS_SIGNALS.items()
        if any(needle in combined for needle in needles)
    ]

    if matched:
        signal = ", ".join(matched[:3]).lower()
        return f"These stories cluster around {signal}, with recurring language related to {theme.lower()}."
    return f"These stories share recurring language related to {theme.lower()}."


def project_embeddings(embeddings: np.ndarray) -> np.ndarray:
    if len(embeddings) < 2:
        return np.zeros((len(embeddings), 2))
    return PCA(n_components=2, random_state=42).fit_transform(embeddings)
