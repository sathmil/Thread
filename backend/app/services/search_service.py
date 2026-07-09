import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings import embed_texts
from app.models import Dataset, Embedding, Story, TextUnit
from app.services.cluster_service import get_theme_by_story_external_id

UNIT_TYPE_MAP = {"Sentences": "sentence", "Passages": "passage", "Stories": "story"}


@dataclass
class SearchResult:
    story_id: str
    unit_type: str
    unit_index: int
    text_unit: str
    preview: str
    score: float
    theme: str | None


def search(
    session: Session,
    dataset: Dataset,
    query: str,
    unit: str,
    top_k: int,
    provider: str = "Local MiniLM",
) -> tuple[list[SearchResult], float]:
    """DB-backed replacement for app.search.search(): embeds the query (reusing
    app.embeddings as-is) then ranks by pgvector cosine distance instead of
    in-memory cosine_similarity. Returns (results, embedding_ms).
    """
    if unit not in UNIT_TYPE_MAP:
        raise ValueError(f"Unsupported search unit: {unit}")
    unit_type = UNIT_TYPE_MAP[unit]

    embed_start = time.perf_counter()
    query_vector = embed_texts([query], provider)[0].tolist()
    embedding_ms = (time.perf_counter() - embed_start) * 1000

    distance = Embedding.vector_384.cosine_distance(query_vector)
    stmt = (
        select(
            Story.external_id,
            TextUnit.unit_type,
            TextUnit.unit_index,
            TextUnit.text_unit,
            TextUnit.preview,
            distance.label("distance"),
        )
        .join(TextUnit, TextUnit.id == Embedding.text_unit_id)
        .join(Story, Story.id == TextUnit.story_id)
        .where(Story.dataset_id == dataset.id, TextUnit.unit_type == unit_type)
        .order_by(distance)
        .limit(top_k)
    )
    rows = session.execute(stmt).all()

    themes = get_theme_by_story_external_id(session, dataset.id)
    results = [
        SearchResult(
            story_id=row.external_id,
            unit_type=row.unit_type,
            unit_index=row.unit_index,
            text_unit=row.text_unit,
            preview=row.preview,
            score=1 - row.distance,
            theme=themes.get(row.external_id),
        )
        for row in rows
    ]
    return results, embedding_ms
