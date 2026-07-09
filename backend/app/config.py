from pathlib import Path
import os


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "stories_metadata.csv"
EMBEDDINGS_PATH = ROOT / "data" / "story_embeddings.npy"
OPENAI_EMBEDDINGS_PATH = ROOT / "data" / "story_embeddings_openai.npy"
EVALUATION_GOLD_PATH = ROOT / "data" / "evaluation_gold.csv"

LOCAL_MODEL_NAME = "all-MiniLM-L6-v2"
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

FOCUS_SIGNALS = {
    "Belonging & Community": ["belong", "community", "welcome", "fit in", "family", "home"],
    "Identity & Representation": ["identity", "culture", "language", "color", "name", "native", "hispanic", "asian"],
    "Voice & Self-Advocacy": ["voice", "speak", "quiet", "heard", "answer", "debate", "raise my hand"],
    "Education & Access": ["school", "books", "internet", "teacher", "classroom", "chemistry", "library"],
    "Care & Mutual Support": ["helping", "mentor", "showing up", "hugs", "support", "together"],
    "Resilience & Growth": ["failure", "practice", "learned", "challenge", "courage", "stronger", "growth"],
}

SEARCH_UNITS = ("Sentences", "Passages", "Stories")
EMBEDDING_BACKENDS = ("Local MiniLM", "OpenAI API")

# Fixed narrative-fingerprint dimensions (roadmap M7.5) — deliberately small
# and stable so radar charts/comparisons stay meaningful. Keyword lists below
# are the deterministic fallback scorer used when no LLM key is configured;
# this is a sibling of FOCUS_SIGNALS above (independent per-dimension scores
# rather than a single best-match tag).
FINGERPRINT_DIMENSIONS = (
    "hope",
    "isolation",
    "identity",
    "family",
    "growth",
    "grief",
    "belonging",
    "agency",
)

FINGERPRINT_KEYWORDS = {
    "hope": ["hope", "hopeful", "future", "better days", "optimis", "dream", "possibility"],
    "isolation": ["alone", "isolat", "lonely", "invisible", "left out", "excluded", "disappear"],
    "identity": ["identity", "who i am", "culture", "language", "heritage", "name", "native"],
    "family": ["family", "mother", "father", "grandmother", "grandfather", "parents", "sister", "brother"],
    "growth": ["learned", "grew", "grow", "practice", "challenge", "overcome", "stronger", "growth"],
    "grief": ["loss", "grief", "mourning", "missing", "gone", "died", "passed away"],
    "belonging": ["belong", "community", "welcome", "home", "fit in", "together"],
    "agency": ["decided", "chose", "voice", "spoke up", "stood up", "took charge", "led", "raise my hand"],
}
