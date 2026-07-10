from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import LOCAL_MODEL_NAME
from app.embeddings import embed_texts
from app.models import Dataset, Embedding, Story, TextUnit
from app.services import fingerprint_service
from app.services.cluster_service import get_theme_by_story_external_id
from app.services.embedding_columns import vector_column_for_model_id
from app.text import make_preview


@dataclass
class MirrorMatch:
    story_id: str
    title: str | None
    preview: str
    score: float
    theme: str | None
    explanation: str


@dataclass
class MirrorResult:
    matches: list[MirrorMatch]
    fingerprint: dict[str, float]
    fingerprint_source: str


def find_matches(session: Session, dataset: Dataset, story_text: str, top_k: int = 3) -> MirrorResult:
    """Embeds pasted text on the fly (local MiniLM — no key required, no
    dataset/account needed) and finds its nearest stored stories via the
    same pgvector cosine-distance query used elsewhere; nothing about the
    pasted text is persisted. Reuses fingerprint_service.score_text() for
    the same LLM-with-keyword-fallback scoring used for stored stories.
    """
    vector = embed_texts([story_text], "Local MiniLM")[0].tolist()
    model_id = LOCAL_MODEL_NAME
    column = vector_column_for_model_id(model_id)
    distance = column.cosine_distance(vector)

    rows = session.execute(
        select(Story, distance.label("distance"))
        .select_from(Story)
        .join(TextUnit, TextUnit.story_id == Story.id)
        .join(Embedding, Embedding.text_unit_id == TextUnit.id)
        .where(
            Story.dataset_id == dataset.id,
            TextUnit.unit_type == "story",
            Embedding.embedding_model == model_id,
        )
        .order_by(distance)
        .limit(top_k)
    ).all()

    themes = get_theme_by_story_external_id(session, dataset.id, model_id)
    own_dimensions, source, _ = fingerprint_service.score_text(story_text)

    matches = []
    for story, dist in rows:
        story_fingerprint = fingerprint_service.compute_fingerprint(session, story)
        explanation = fingerprint_service.explain_similarity(own_dimensions, story_fingerprint.dimensions)
        matches.append(
            MirrorMatch(
                story_id=story.external_id,
                title=story.title,
                preview=make_preview(story.story_text),
                score=round(1 - dist, 4),
                theme=themes.get(story.external_id),
                explanation=explanation,
            )
        )

    return MirrorResult(matches=matches, fingerprint=own_dimensions, fingerprint_source=source)
