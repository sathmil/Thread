import os

from app.config import LOCAL_MODEL_NAME, OPENAI_EMBEDDING_MODEL
from app.models import Embedding

# The two supported providers map to different fixed-width vector columns
# (MiniLM=384, OpenAI text-embedding-3-small=1536) rather than one variable-
# width column — see the roadmap's embedding-dimension decision. Centralizing
# the provider->column mapping here so search/cluster/index all agree on it.
#
# "Local MiniLM" / "OpenAI API" are provider *labels* — they select which
# embed_texts() codepath runs (dispatch). The actual model identifier
# ("all-MiniLM-L6-v2", "text-embedding-3-small") is what's stored in and
# queried from Embedding.embedding_model / Cluster.embedding_model, so two
# different model versions could coexist and be told apart. Conflating the
# two was a real bug caught in M7: the seed script stored LOCAL_MODEL_NAME,
# while indexing/search code was filtering by the provider label instead —
# silently returning zero rows for the seed dataset.

_DIM_BY_PROVIDER = {"Local MiniLM": 384, "OpenAI API": 1536}
_MODEL_ID_BY_PROVIDER = {"Local MiniLM": LOCAL_MODEL_NAME, "OpenAI API": OPENAI_EMBEDDING_MODEL}
_DIM_BY_MODEL_ID = {LOCAL_MODEL_NAME: 384, OPENAI_EMBEDDING_MODEL: 1536}


def dim_for_provider(provider: str) -> int:
    return _DIM_BY_PROVIDER.get(provider, 384)


def vector_column(provider: str):
    """For when you have a provider label (e.g. from a search/index request)."""
    return Embedding.vector_1536 if dim_for_provider(provider) == 1536 else Embedding.vector_384


def model_id_for_provider(provider: str) -> str:
    """The actual model identifier stored in Embedding/Cluster.embedding_model
    for a given provider label. Falls back to the provider string itself if
    it's not a recognized label (e.g. it's already a model id).
    """
    return _MODEL_ID_BY_PROVIDER.get(provider, provider)


def dim_for_model_id(model_id: str) -> int:
    return _DIM_BY_MODEL_ID.get(model_id, 384)


def vector_column_for_model_id(model_id: str):
    """For when you only have a stored model id (e.g. resolved from an
    existing Cluster/Embedding row), not a provider label.
    """
    return Embedding.vector_1536 if dim_for_model_id(model_id) == 1536 else Embedding.vector_384


def vector_kwargs(vector) -> dict:
    """Given an embedded vector, returns the {vector_384: ...} or
    {vector_1536: ...} kwarg (plus dim) to construct an Embedding row —
    dimension-driven, not provider-driven, so it's correct even if a new
    provider is added later without updating every call site.
    """
    dim = len(vector)
    values = vector.tolist() if hasattr(vector, "tolist") else list(vector)
    if dim == 1536:
        return {"vector_1536": values, "dim": dim}
    return {"vector_384": values, "dim": dim}


def resolve_provider(requested_model: str) -> tuple[str, str | None]:
    """app.embeddings.embed_texts() silently falls back to local MiniLM if
    OpenAI is requested without OPENAI_API_KEY set. Resolving the actual
    provider up front lets callers both label/query stored embeddings
    correctly and surface the fallback as a visible warning instead of a
    silent mismatch between what was requested and what's actually stored.
    """
    if requested_model == "OpenAI API" and not os.getenv("OPENAI_API_KEY"):
        return "Local MiniLM", "OPENAI_API_KEY is not set — used Local MiniLM instead of OpenAI API."
    return requested_model, None
