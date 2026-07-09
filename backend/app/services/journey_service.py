from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Embedding, Story, TextUnit
from app.services.embedding_columns import vector_column_for_model_id


def _story_level_embedding(session: Session, story: Story) -> tuple[list[float], str] | None:
    row = session.execute(
        select(Embedding.vector_384, Embedding.vector_1536, Embedding.embedding_model)
        .join(TextUnit, TextUnit.id == Embedding.text_unit_id)
        .where(TextUnit.story_id == story.id, TextUnit.unit_type == "story")
        .limit(1)
    ).first()
    if row is None:
        return None
    vector_384, vector_1536, model_id = row
    vector = vector_384 if vector_384 is not None else vector_1536
    return vector, model_id


def nearest_and_farthest(
    session: Session, story: Story, top_k: int = 3
) -> tuple[list[tuple[Story, float]], tuple[Story, float] | None]:
    """Returns (nearest neighbors, most-dissimilar "contrasting" story), both
    restricted to the same dataset and the same embedding model as the
    story's own whole-story embedding, via pure pgvector distance queries —
    no new inference cost, reuses embeddings already computed in M1/M6.
    """
    self_embedding = _story_level_embedding(session, story)
    if self_embedding is None:
        return [], None
    self_vector, model_id = self_embedding

    column = vector_column_for_model_id(model_id)
    distance = column.cosine_distance(self_vector)

    base_query = (
        select(Story, distance.label("distance"))
        .select_from(Story)
        .join(TextUnit, TextUnit.story_id == Story.id)
        .join(Embedding, Embedding.text_unit_id == TextUnit.id)
        .where(
            Story.dataset_id == story.dataset_id,
            TextUnit.unit_type == "story",
            Embedding.embedding_model == model_id,
            Story.id != story.id,
        )
    )

    nearest_rows = session.execute(base_query.order_by(distance).limit(top_k)).all()
    farthest_row = session.execute(base_query.order_by(distance.desc()).limit(1)).first()

    nearest = [(row[0], 1 - row[1]) for row in nearest_rows]
    farthest = (farthest_row[0], 1 - farthest_row[1]) if farthest_row else None
    return nearest, farthest
