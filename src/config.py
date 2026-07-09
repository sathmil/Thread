from pathlib import Path
import os


ROOT = Path(__file__).resolve().parents[1]
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
