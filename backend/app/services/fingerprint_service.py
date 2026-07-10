import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import llm
from app.config import FINGERPRINT_DIMENSIONS, FINGERPRINT_KEYWORDS
from app.llm import DEFAULT_MODEL
from app.models import Story, StoryFingerprint

KEYWORD_MODEL_ID = "keyword-heuristic-v1"
FINGERPRINT_VERSION = "v1"

# A keyword can appear many times in a long story without the dimension
# being any more "true" past a point — soft-cap the hit count before
# normalizing to 0-1 rather than letting raw counts dominate.
_KEYWORD_HIT_CAP = 5


def _keyword_fingerprint(story_text: str) -> dict[str, float]:
    lowered = story_text.lower()
    scores = {}
    for dimension in FINGERPRINT_DIMENSIONS:
        needles = FINGERPRINT_KEYWORDS[dimension]
        hits = sum(lowered.count(needle) for needle in needles)
        scores[dimension] = round(min(1.0, hits / _KEYWORD_HIT_CAP), 3)
    return scores


def _llm_fingerprint(story_text: str) -> dict[str, float] | None:
    if not llm.is_available():
        return None
    prompt = (
        "Score this personal narrative from 0.0 to 1.0 on each of these dimensions: "
        f"{', '.join(FINGERPRINT_DIMENSIONS)}. Respond with ONLY a JSON object mapping "
        "each dimension name to a number between 0 and 1 — no other text.\n\n"
        f"Story:\n{story_text[:3000]}"
    )
    try:
        raw = llm.generate_text(
            prompt, system="You are a careful, literal literary analyst.", max_tokens=200, temperature=0.0
        )
        data = json.loads(raw)
        return {dimension: max(0.0, min(1.0, float(data.get(dimension, 0.0)))) for dimension in FINGERPRINT_DIMENSIONS}
    except Exception:
        return None


def score_text(text: str) -> tuple[dict[str, float], str, str]:
    """Returns (dimensions, source, model): tries the LLM first, falls back
    to the deterministic keyword scorer on any failure or missing API key.
    Shared by compute_fingerprint's cached-and-persisted path (below) and
    mirror_service's ad hoc, uncached scoring of pasted (non-Story) text —
    the same provider-dispatch-with-fallback pattern used throughout, just
    without a Story row to cache against.
    """
    llm_scores = _llm_fingerprint(text)
    if llm_scores is not None:
        return llm_scores, "llm", DEFAULT_MODEL
    return _keyword_fingerprint(text), "rule_based", KEYWORD_MODEL_ID


def compute_fingerprint(session: Session, story: Story) -> StoryFingerprint:
    """Returns the cached fingerprint if one already exists for this story
    (versioned the same way as embeddings — see the roadmap), otherwise
    computes and persists one via score_text().
    """
    existing = session.execute(
        select(StoryFingerprint).where(
            StoryFingerprint.story_id == story.id,
            StoryFingerprint.version == FINGERPRINT_VERSION,
        )
    ).scalars().first()
    if existing is not None:
        return existing

    dimensions, source, model = score_text(story.story_text)

    fingerprint = StoryFingerprint(
        story_id=story.id,
        model=model,
        version=FINGERPRINT_VERSION,
        dimensions=dimensions,
        summary_source=source,
    )
    session.add(fingerprint)
    session.commit()
    session.refresh(fingerprint)
    return fingerprint


def dominant_dimensions(fingerprint: StoryFingerprint, top_n: int = 2) -> list[str]:
    ranked = sorted(fingerprint.dimensions.items(), key=lambda item: item[1], reverse=True)
    return [dimension for dimension, _ in ranked[:top_n]]


_REFLECTION_QUESTION_TEMPLATES = {
    "hope": "What gave you hope in a moment like this?",
    "isolation": "When have you felt this kind of distance from others, and what helped?",
    "identity": "What part of your own identity does this story bring to mind?",
    "family": "What role has family played in a similar moment in your life?",
    "growth": "What did you learn about yourself the last time you grew through something hard?",
    "grief": "How have you carried a loss like this one?",
    "belonging": "Where have you found a sense of belonging like this?",
    "agency": "When have you found your own voice the way this story describes?",
}


def reflection_questions(fingerprint: StoryFingerprint, top_n: int = 2) -> list[str]:
    return [_REFLECTION_QUESTION_TEMPLATES[dimension] for dimension in dominant_dimensions(fingerprint, top_n)]


def explain_similarity(dims_a: dict[str, float], dims_b: dict[str, float]) -> str:
    """Grounded in the actual fingerprint deltas — the LLM (when available)
    only phrases a computed comparison, it never invents the similarity
    itself, per the roadmap's explicit design for this feature. Takes plain
    dimension dicts (not StoryFingerprint rows) so it works equally for two
    stored stories (M7.5) or one stored story plus an ad hoc, unpersisted
    piece of text (M8.7's "mirror my story").
    """
    shared_high = sorted(
        ((dimension, (dims_a[dimension] + dims_b[dimension]) / 2) for dimension in FINGERPRINT_DIMENSIONS),
        key=lambda item: item[1],
        reverse=True,
    )[:2]
    shared_dims = [dimension for dimension, _ in shared_high]

    biggest_diff = max(
        ((dimension, dims_a[dimension] - dims_b[dimension]) for dimension in FINGERPRINT_DIMENSIONS),
        key=lambda item: abs(item[1]),
    )
    diff_dimension, diff_value = biggest_diff
    leans_toward = "the first story" if diff_value > 0 else "the second story"

    shared_text = " and ".join(shared_dims) if shared_dims else "similar themes"

    if llm.is_available():
        prompt = (
            f"Two personal stories both score relatively high on {shared_text}. "
            f"They differ most on {diff_dimension} ({leans_toward} scores higher). "
            "In exactly one or two warm, plain-language sentences, explain why these stories might "
            "resonate with the same reader. Do not invent plot details — only reason from these dimension scores."
        )
        try:
            return llm.generate_text(prompt, max_tokens=100)
        except Exception:
            pass

    return (
        f"Both stories score high on {shared_text}, though {leans_toward} leans more toward {diff_dimension}."
    )
